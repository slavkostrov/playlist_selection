# playlist_selection

Our project available on [web page](http://51.250.97.70:5000/) and also in TG bot [@playlist_selection_bot](https://t.me/playlist_selection_bot) ([bot's description](https://github.com/Hul1Ganych/ps-tg-bot/tree/master)).

The application registered on the Spotify side is currently in the “development” status, so to get full access to the functionality of the service, users need to be entered in the Spotify dashboard, so if you need this, please write to the developers. At the same time, the **telegram bot is available in full**.

## Description

Generating playlists based on selected tracks/Spotify profile/Ya.Muzik/Apple Music.
1. Entrance:
- Account details
- List of tracks for generating a similar playlist (all tracks/ready playlist/separate list of tracks)
- Additionally: characteristics of the generated playlist (mood, etc.)

2. Output:
- Link to a playlist with the most similar tracks

## Architecture

![Без имени](https://github.com/slavkostrov/playlist_selection/assets/64536258/bf7a63bc-9968-4047-8f35-214818eb7951)

## Example

Here you can see example of out web app:

![ezgif-3-5b3fa1551f](https://github.com/slavkostrov/playlist_selection/assets/64536258/96d7be11-4e60-4779-a036-25baa1f3f23e)

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

## Project structure

* /playlist_selection - library with parser, downloader and some model tools;
* /app - fastapi app implemntation;
* /bot - submodule with bot implementation.

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
PLAYLIST_SELECTION_S3_ENDPOINT_URL=
PLAYLIST_SELECTION_S3_BUCKET_NAME=
PLAYLIST_SELECTION_S3_PROFILE_NAME=
PLAYLIST_SELECTION_MODEL_NAME=
PLAYLIST_SELECTION_MODEL_CLASS=
BOT_TOKEN=

PLAYLIST_SELECTION_PGUSER=
PLAYLIST_SELECTION_PGPASSWORD=
PLAYLIST_SELECTION_PGHOST=
PLAYLIST_SELECTION_PGPORT=
PLAYLIST_SELECTION_PGDATABASE=
PLAYLIST_SELECTION_PGSSLMODE=
PLAYLIST_SELECTION_PGSSLROOTCERT=

PLAYLIST_SELECTION_REDIS_HOST=
PLAYLIST_SELECTION_REDIS_PORT=

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=
AWS_ENDPOINT_URL=
```
2. Run docker-compose with `docker-compose up --build`

#### Tests

Run tests with:

```bash
docker-compose run pytest
```

You can specify any pytest's flags, for example:

```bash
docker-compose run pytest --pdb
```

## Authors

* Saraev Nikita [@oldsosa](https://t.me/oldsosa)
* Ganych Daniil [@mercyfu1_fate](https://t.me/mercyfu1_fate)
* Kostrov Vyacheslav [@slavkostrov](https://t.me/slavkostrov)
