PY?=python3
VENV?=.venv
PIP=$(VENV)/bin/pip

.PHONY: help setup venv install clean test

help:
	@echo "Targets:"
	@echo "  make setup   - create .venv and install requirements"
	@echo "  make venv    - create .venv"
	@echo "  make install - install requirements into .venv"
	@echo "  make test    - run unit tests via .venv"
	@echo "  make clean   - remove .venv"

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

setup: install
	@echo "Virtualenv ready at $(VENV)"

test: install
	$(VENV)/bin/python -m unittest discover -v

clean:
	rm -rf $(VENV)
