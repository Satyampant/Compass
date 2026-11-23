.PHONY: dev test lint e2e build install uninstall restart logs restore

PLIST := $(HOME)/Library/LaunchAgents/com.compass.app.plist
DOMAIN := gui/$(shell id -u)

dev:
	COMPASS_BACKGROUND=0 uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

e2e: build
	uv run pytest -q e2e

build:
	cd web && npm ci --silent && npm run build

install: build
	mkdir -p $(HOME)/Library/Logs/Compass $(HOME)/Library/LaunchAgents
	sed -e 's#__ROOT__#$(CURDIR)#g' -e 's#__HOME__#$(HOME)#g' run/com.compass.app.plist > $(PLIST)
	-launchctl bootout $(DOMAIN)/com.compass.app 2>/dev/null
	launchctl bootstrap $(DOMAIN) $(PLIST)

uninstall:
	-launchctl bootout $(DOMAIN)/com.compass.app
	rm -f $(PLIST)

restart:
	launchctl kickstart -k $(DOMAIN)/com.compass.app

logs:
	tail -f $(HOME)/Library/Logs/Compass/compass.log

restore:  ## make restore BACKUP=path/to/compass-YYYY-MM-DD.db INTO=scratch/folder
	uv run python -m app.kernel.backup restore $(BACKUP) $(INTO)
