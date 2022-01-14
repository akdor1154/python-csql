

test:
	poetry run pytest
	cd docs; poetry run $(MAKE) doctest

docs:
	cd docs; poetry run $(MAKE) html SPHINXOPTS="-W --keep-going -n"

.PHONY: test docs
