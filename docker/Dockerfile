FROM python:3.10.6-slim AS python-base

ARG PROJECT_HOME=/playlist-selection-app
ARG BUILD_HOME=/opt/build

ENV PYTHONUNBUFFERED true
ENV PYTHONDONTWRITEBYTECODE true
ENV PIP_NO_CACHE_DIR true
ENV PIP_DISABLE_PIP_VERSION_CHECK true

FROM python-base as python-base-with-poetry

ARG POETRY_VERSION=1.8.2
ARG BUILD_HOME=/opt/build

ENV POETRY_VIRTUALENVS_IN_PROJECT true
ENV POETRY_NO_INTERACTION true
ENV PATH="${BUILD_HOME}/.venv/bin:${PATH}"

RUN set -ex && \
    mkdir -p ${BUILD_HOME} && \
    apt-get update -yqq && \
    apt-get install -yqq curl git && \
    python -m pip install poetry==${POETRY_VERSION} && \
    python -m pip install poetry-dynamic-versioning && \
    python -m pip check
WORKDIR ${BUILD_HOME}


FROM python-base-with-poetry as builder
ARG BUILD_HOME=/opt/build
COPY . ${BUILD_HOME}
RUN poetry build --format wheel


FROM python-base-with-poetry as dev
ARG BUILD_HOME=/opt/build
ARG PROJECT_HOME=/playlist-selection-app
COPY docker/scripts /usr/local/bin/
RUN chmod +x /usr/local/bin/*_db.sh

# Speed up image build
COPY poetry.lock pyproject.toml ${BUILD_HOME}/
RUN poetry install --no-plugins --no-root --without research

# Setup
COPY --from=builder ${BUILD_HOME}/dist/*.whl ${BUILD_HOME}
RUN python -m pip install playlist_selection*.whl && \
    rm playlist_selection*.whl


COPY migrations $PROJECT_HOME/migrations
COPY alembic.ini $PROJECT_HOME
WORKDIR ${PROJECT_HOME}


FROM python-base as production
ARG BUILD_HOME=/opt/build
ENV HOME /home/user
ENV APP_HOME ${HOME}/app
RUN mkdir -p ${HOME}
RUN groupadd -r user && \
    useradd -r -g user -d ${HOME} -s /sbin/nologin -c "Docker image user" user && \
    chown -R user:user ${HOME}
USER user
ENV PATH="/home/user/.local/bin:${PATH}"

COPY --from=builder --chown=user ${BUILD_HOME}/dist/*.whl ${HOME}
COPY --chown=user docker/scripts/ /usr/local/bin/
COPY --chown=user app/logging_config.yml /usr/local/conf/logging_config.yml
RUN chmod +x /usr/local/bin/*_db.sh

RUN python -m pip install ${HOME}/playlist_selection*.whl && \
    rm ${HOME}/playlist_selection*.whl && \
    mkdir -p ${APP_HOME}

WORKDIR ${APP_HOME}

COPY migrations $APP_HOME/migrations
COPY alembic.ini $APP_HOME
