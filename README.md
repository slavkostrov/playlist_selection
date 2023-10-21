# playlist_selection

## Developement

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

```bash
poetry run pytest -vv tests
```
