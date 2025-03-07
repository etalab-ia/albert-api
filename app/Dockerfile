FROM python:3.12-slim

RUN groupadd --gid 1100 albert
RUN useradd --home /home/albert --gid 1100 --uid 1100 albert 
USER albert
ENV PATH="/home/albert/.local/bin:${PATH}"

WORKDIR /home/albert
ADD ./pyproject.toml ./pyproject.toml
RUN pip install ".[app]"
ADD ./app /home/albert/app
ENV PYTHONPATH="/home/albert/app:${PYTHONPATH}"

RUN alembic upgrade head