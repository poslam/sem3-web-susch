FROM python:3.11

ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry

ENV PATH="${PATH}:${POETRY_VENV}/bin"

EXPOSE 8001

WORKDIR /api

COPY poetry.lock pyproject.toml ./
RUN poetry install

COPY . /api

CMD ["poetry", "run", "python", "-m", "uvicorn", "src.app:app", "--port", "8001", "--host", "0.0.0.0"]