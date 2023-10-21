# playlist_selection

## Developement

* Poetry

Install poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

* Linters
  
Setup pre-commit hooks:

```bash
pre-commit install
```

Check code quality with `ruff`:
```bash
ruff check --config pyproject.toml .
```

Fix code with `ruff`:
```bash
ruff check --config pyproject.toml --fix .
```

VSCode supports `ruff` [extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff).
