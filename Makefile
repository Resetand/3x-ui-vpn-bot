PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
PID_FILE := .bot.pid

.PHONY: venv vendor start stop restart status logs clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

venv: ## Create Python virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "venv created at $(VENV). Activate: source $(BIN)/activate"

vendor: | venv ## Install dependencies into venv
	$(BIN)/pip install -r requirements.txt

start: ## Start the bot (background)
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Bot is already running (PID $$(cat $(PID_FILE)))"; \
	else \
		$(BIN)/python -m bot >> bot.log 2>&1 & echo $$! > $(PID_FILE); \
		echo "Bot started (PID $$(cat $(PID_FILE))), logs: bot.log"; \
	fi

stop: ## Stop the bot
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		kill $$(cat $(PID_FILE)) && rm -f $(PID_FILE); \
		echo "Bot stopped"; \
	else \
		rm -f $(PID_FILE); \
		echo "Bot is not running"; \
	fi

restart: stop start ## Restart the bot

status: ## Check if the bot is running
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "Bot is running (PID $$(cat $(PID_FILE)))"; \
	else \
		rm -f $(PID_FILE); \
		echo "Bot is not running"; \
	fi

logs: ## Tail bot logs
	@tail -f bot.log

clean: ## Remove venv and build artifacts
	rm -rf $(VENV) __pycache__ bot/__pycache__ bot/**/__pycache__ .bot.pid bot.log
