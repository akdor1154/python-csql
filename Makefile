lint: mypy

mypy:
	poetry run mypy csql tests

test: pytest doctest

pytest:
	poetry run pytest

doctest:
	cd docs; poetry run $(MAKE) doctest

docs:
	cd docs; poetry run $(MAKE) html SPHINXOPTS="-W --keep-going -n"

.PHONY: test docs lint mypy pytest doctest
