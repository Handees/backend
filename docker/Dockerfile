FROM python:3.13-bullseye

ARG COCKROACH_DB_CERT_URL
ARG DATABASE_CERT_PATH
ARG DATABASE_CERT_DIR_PATH

# Create a group and user
RUN groupadd -r handeesofficial && useradd -r -g handeesofficial handeesofficial

WORKDIR /home/handeesofficial/backend

RUN apt update && apt install nginx -y && apt install less -y && apt install vim -y
COPY nginx/server.conf /etc/nginx/sites-available
RUN ln -s /etc/nginx/sites-available/server.conf /etc/nginx/sites-enabled/server.conf && rm /etc/nginx/sites-enabled/default

# install cert for cockroachDB
RUN curl --create-dirs -o ${DATABASE_CERT_PATH} ${COCKROACH_DB_CERT_URL}
RUN chown handeesofficial:handeesofficial ${DATABASE_CERT_PATH}
RUN chown handeesofficial:handeesofficial ${DATABASE_CERT_DIR_PATH}


# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt ./

# create & activate venv
RUN python3 -m venv env
ENV PATH="/home/handeesofficial/backend/env/bin:$PATH"

# upgrade pip and install dependencies
RUN echo "[Before requirements] pip path:" && which pip && pip --version && echo $PATH
RUN pip install -r requirements.txt
RUN echo "[Before requirements] pip path:" && which pip && pip --version && echo $PATH
RUN pip install gunicorn
RUN pip install supervisor
RUN pip install sqlalchemy-cockroachdb

COPY . .


CMD [ "env/bin/supervisord", "-c", "supervisord-dev.conf"]
