# playlist_selection

## Description

__TODO__

## Examples

__TODO__

## Project structure

__TODO__

## Development

Create new branch from `master` to add new feature. Create Pull Requests with new changes, add tests and check code quality.

#### Poetry

Install poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add dependency with:
```bash
poetry add flask
```

#### Linters
  
Setup pre-commit hooks:

```bash
pre-commit install
```

Check code quality with `ruff`:
```bash
poetry ruff check --config pyproject.toml .
```

Fix code with `ruff`:
```bash
poetry ruff check --config pyproject.toml --fix .
```

VSCode supports `ruff` [extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff).


#### Tests

Without coverage report:

```bash
poetry run pytest -vv tests
```

Coverage report:
```bash
poetry run pytest --cov=src --cov-fail-under=60 tests/
```

## Authors

__TODO__