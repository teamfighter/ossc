PY?=python3
VENV?=.venv
PIP=$(VENV)/bin/pip

.PHONY: help setup venv install clean

help:
	@echo "Targets:"
	@echo "  make setup   - create .venv and install requirements"
	@echo "  make venv    - create .venv"
	@echo "  make install - install requirements into .venv"
	@echo "  make clean   - remove .venv"

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

setup: install
	@echo "Virtualenv ready at $(VENV)"

clean:
	rm -rf $(VENV)

