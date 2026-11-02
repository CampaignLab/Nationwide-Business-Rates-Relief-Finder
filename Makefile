PYTHON ?= .venv/bin/python

.PHONY: all test setup

all:
	$(PYTHON) run_all.py

test:
	$(PYTHON) -m pytest -q tests

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
