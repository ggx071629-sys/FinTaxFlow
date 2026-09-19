.PHONY: start check stop stop-all

start:
	./start.sh $(ARGS)

check:
	./start.sh --check

stop:
	./scripts/stop.sh

stop-all:
	./scripts/stop.sh --all
