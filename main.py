import logging
import sys
import time

from inbibe_bot.config import AppConfig, ConfigError
from inbibe_bot.core.booking_workflow import BookingWorkflow
from inbibe_bot.core.formatter import BookingFormatter
from inbibe_bot.client.bot_factory import Deps, build_bot, register_all_handlers
from inbibe_bot.logging_config import setup_logging
from inbibe_bot.server.http_server import build_server
from inbibe_bot.server.routes import ServerDeps
from inbibe_bot.storage.booking_repository import BookingRepository
from inbibe_bot.storage.delivery_queue import ApprovedBookingQueue
from inbibe_bot.storage.ephemeral_messages import EphemeralMessageService
from inbibe_bot.storage.persistence import StatePersister
from inbibe_bot.storage.user_flow_repository import UserFlowRepository


if __name__ == "__main__":
    setup_logging()

    try:
        config = AppConfig.from_env()
    except ConfigError as e:
        logging.error("Ошибка конфигурации: %s", e)
        sys.exit(1)

    # --- Зависимости ---
    bot = build_bot(config)
    booking_repo = BookingRepository()
    flow_repo = UserFlowRepository()
    delivery_queue = ApprovedBookingQueue()
    ephemeral = EphemeralMessageService(bot)
    workflow = BookingWorkflow(allowed_tables=set(config.actual_tables))
    formatter = BookingFormatter()

    deps = Deps(
        bot=bot,
        config=config,
        booking_repo=booking_repo,
        flow_repo=flow_repo,
        delivery_queue=delivery_queue,
        ephemeral=ephemeral,
        workflow=workflow,
        formatter=formatter,
    )

    # --- Persistence ---
    persister = StatePersister(
        path=config.state_file,
        bookings=booking_repo,
        flows=flow_repo,
        queue=delivery_queue,
        ephemeral=ephemeral,
    )
    persister.load()

    # Сохранять при каждом изменении — надёжнее чем atexit в Docker
    for repo in (booking_repo, flow_repo, delivery_queue, ephemeral):
        repo.set_change_callback(persister.save)

    # --- Регистрация хэндлеров ---
    register_all_handlers(deps)

    # --- Прокси ---
    import telebot.apihelper as _apihelper
    if config.tg_proxy:
        _apihelper.proxy = {"https": config.tg_proxy}  # type: ignore[assignment]
        logging.info("Прокси для Telegram: %s", config.tg_proxy)
    else:
        logging.info("Прокси для Telegram: не задан")

    # --- HTTP сервер (нужен в обоих режимах) ---
    server_deps = ServerDeps(
        bot=bot,
        admin_group_id=config.admin_group_id,
        webhook_secret=config.webhook_secret,
        booking_repo=booking_repo,
        delivery_queue=delivery_queue,
        formatter=formatter,
    )

    logging.info("Режим запуска: %s", config.tg_mode)

    if config.tg_mode == "polling":
        import threading
        bot.remove_webhook()

        http_server = build_server(server_deps, config.http_port)
        threading.Thread(
            target=http_server.serve_forever,
            daemon=True,
            name="http-server",
        ).start()
        logging.info("HTTP сервер запущен на порту %s (фоновый поток)", config.http_port)

        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except KeyboardInterrupt:
            logging.info("Остановка бота...")
        finally:
            http_server.shutdown()
            bot.remove_webhook()

    else:  # webhook
        if not config.webhook_url:
            logging.error("WEBHOOK_URL не задан, запуск невозможен")
            sys.exit(1)

        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=config.webhook_url + "/webhook", secret_token=config.webhook_secret)
        logging.info("Webhook установлен: %s/webhook", config.webhook_url)

        try:
            with build_server(server_deps, config.http_port) as httpd:
                logging.info("HTTP сервер запущен на порту %s", config.http_port)
                httpd.serve_forever()
        except KeyboardInterrupt:
            logging.info("Остановка бота...")
        finally:
            bot.remove_webhook()
            logging.info("Webhook удален")
