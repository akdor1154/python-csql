lint: mypy ruff

ruff:
	uv run ruff check
	uv run ruff format --check

mypy:
	uv run mypy csql tests

test: pytest doctest

pytest:
	uv run pytest

doctest:
	cd docs; uv run $(MAKE) doctest

docs:
	cd docs; uv run $(MAKE) html SPHINXOPTS="-W --keep-going -n"

.PHONY: test docs lint mypy pytest doctest
