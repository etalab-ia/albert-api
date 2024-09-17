FROM python:3.12-slim

# @TODO: non root image
WORKDIR /app


COPY pyproject.toml .
RUN pip install ".[ui]"

COPY ./ui .
