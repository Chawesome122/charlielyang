.PHONY: install test reproduce reproduce-full manuscript fetch
PYTHON := .venv/bin/python
install:
	UV_CACHE_DIR=/workspace/.cache/uv uv sync --frozen
test:
	$(PYTHON) -m pytest -q --junitxml=outputs/diagnostics/pytest.xml
reproduce:
	$(PYTHON) scripts/replicate.py
reproduce-full:
	$(PYTHON) scripts/replicate.py --full
manuscript:
	cd manuscript && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
fetch:
	$(PYTHON) scripts/fetch.py
