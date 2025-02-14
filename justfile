# Relative to docs/
sphinxbuild := "../.venv/bin/sphinx-build"

@_default:
    just --list

# Build a dev environment
devenv:
    uv sync --extra dev --refresh --upgrade

# Run tests and linting
test *args: devenv
    uv run tox {{args}}

# Run typechecking
typecheck: devenv
    uv run tox -e py39-typecheck

# Format files
format: devenv
    uv run tox exec -e py39-lint -- ruff format

# Lint files
lint: devenv
    uv run tox -e py39-lint

# Clean development and build artifacts
clean:
    rm -rf .venv uv.lock
    rm -rf build dist src/fillmore.egg-info .tox .pytest_cache .mypy_cache
    rm -rf docs/_build/*
    find src/ tests/ -name __pycache__ | xargs rm -rf
    find src/ tests/ -name '*.pyc' | xargs rm -rf


# Runs cog and builds Sphinx docs
docs: devenv
    uv run python -m cogapp -r README.rst
    uv run python -m cogapp -r docs/scrubber.rst
    uv run python -m cogapp -r docs/testing.rst
    SPHINXBUILD={{sphinxbuild}} make -e -C docs/ clean html
