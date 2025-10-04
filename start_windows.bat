@echo off
set "api_key=твой_токен_бота"
set "admin_group_id=id_админ_группы"

cd /d "%~dp0"
start "" python main.py
