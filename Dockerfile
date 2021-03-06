FROM python:3.8

WORKDIR /src

ENV PATH="/root/.poetry/bin:${PATH}"

ARG POETRY_VERSION
ENV POETRY_VERSION="${POETRY_VERSION:-1.1.6}"
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py \
  | python - --version "${POETRY_VERSION}" \
 && poetry --version


COPY poetry.lock pyproject.toml ./
COPY event_notification_handler.py ./

RUN poetry install
CMD poetry run kopf run /src/event_notification_handler.py --log-format=json --verbose