include .env.makefile
include .env.prod

export

dh_login:
	dockhost config login -u $(DH_LOGIN) -p $(DH_PASSWORD)
	dockhost project use inbibe-order-bot

release:
	@if [ -z "$(VERSION)" ]; then echo "ERROR: VERSION is required. Usage: make release VERSION=1.0.0"; exit 1; fi
	@if [ -z "$(DOCKER_LOGIN)" ] || [ -z "$(DOCKER_PASSWORD)" ]; then echo "ERROR: DOCKER_LOGIN and DOCKER_PASSWORD are required"; exit 1; fi
	@echo "$(DOCKER_PASSWORD)" | docker login -u "$(DOCKER_LOGIN)" --password-stdin
	git tag v$(VERSION)
	git push origin v$(VERSION)
	docker login
	docker build -t akas1j/inbibe-order-bot:v$(VERSION) -t akas1j/inbibe-order-bot:latest .
	docker push akas1j/inbibe-order-bot:v$(VERSION)
	docker push akas1j/inbibe-order-bot:latest

deploy:
	dockhost compose apply ./dockhost.yaml

check_tg_hook:
	curl https://api.telegram.org/bot$(TG_API_KEY)/getWebhookInfo

