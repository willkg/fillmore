DEFAULT_GOAL := help
PROJECT=fillmore

.PHONY: help
help:
	@echo "Available rules:"
	@echo ""
	@fgrep -h "##" Makefile | fgrep -v fgrep | sed 's/\(.*\):.*##/\1:  /'

.PHONY: test
test:  ## Run tests
	tox

.PHONY: typecheck
typecheck:  ## Run typechecking
	tox -e py38-typecheck

.PHONY: lint
lint:  ## Lint and reformat files
	black src setup.py tests docs examples
	tox -e py38-lint

.PHONY: clean
clean:  ## Clean build artifacts
	rm -rf build dist src/${PROJECT}.egg-info .tox .pytest_cache .mypy_cache
	rm -rf docs/_build/*
	find src/ tests/ -name __pycache__ | xargs rm -rf
	find src/ tests/ -name '*.pyc' | xargs rm -rf

.PHONY: docs
docs:  ## Runs cog and builds Sphinx docs
	python -m cogapp -d -o README.rst docs_tmpl/README.rst
	python -m cogapp -d -o docs/scrubber.rst docs_tmpl/scrubber.rst
	python -m cogapp -d -o docs/testing.rst docs_tmpl/testing.rst
	make -C docs/ clean html

.PHONY: checkrot
checkrot:  ## Check package rot for dev dependencies
	pip list -o
