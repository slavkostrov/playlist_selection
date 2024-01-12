# playlist_selection

## Description

Generating playlists based on selected tracks/Spotify profile/Ya.Muzik/Apple Music.
1. Entrance:
- Account details
- List of tracks for generating a similar playlist (all tracks/ready playlist/separate list of tracks)
- Additionally: characteristics of the generated playlist (mood, etc.)

2. Output:
- Link to a playlist with the most similar tracks

## Plan

Work plan

What tasks will be done at the first stage (exploratory data analysis and primary data analytics)
* Think about how we will collect data and where?
* How much data do you need? (not too much in the first step)
* Think about where we will store everything
* Think about resources in general

  
What tasks will be done in the second stage (ML)
* Think about audio presentation
* You can try ready-made ones on mvp
* Encodec
* See what else is there
* Vector search
* See what libraries faiss, qdrant are available
  
What tasks will be done in the third stage (DL)
* We can try to train our own (we can use any meta audio), metric learning, triplet loss
* Think over the architecture (you can look for a ready-made one)
* yandex ml cup 2022 find a problem, see what solutions were there (task of finding identical authors)
What tasks would you like to do, but perhaps you won’t have time to do (link them to the necessary stages)

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

#### Docker

1. Create .env file with tokens
```.env
PLAYLIST_SELECTION_CLIENT_ID=
PLAYLIST_SELECTION_CLIENT_SECRET=
PLAYLIST_SELECTION_CALLBACK_URL=
```
2. Run docker-compose with `docker-compose up --build`

Copy your AWS creds in current directory.

#### Tests

Without coverage report:

```bash
poetry run pytest -vv tests
```

Coverage report:
```bash
poetry run pytest --cov=src --cov-fail-under=60 tests/
```

#### Jupyter

__TODO__

## Authors

* Saraev Nikita
* Ganych Daniil
* Kostrov Vyacheslav
