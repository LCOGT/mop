FROM python:3.10.11
LABEL maintainer="rstreet@lco.global"

WORKDIR /mop

RUN pip install poetry

COPY ./pyproject.toml ./poetry.lock ./poetry.toml /mop

RUN poetry install --no-root --only main

COPY . /mop

# Activate virtual env
ENV PATH="/mop/.venv/bin:$PATH"

# disable buffering so that logs are rendered to stdout asap
ENV PYTHONUNBUFFERED=1

# the exposed port must match the deployment.yaml containerPort value
EXPOSE 80

ENTRYPOINT [ "gunicorn", "mop.wsgi", "-b", "0.0.0.0:80", "--access-logfile", "-", "--error-logfile", "-", "-k", "gevent", "--timeout", "300", "--workers", "2"]
