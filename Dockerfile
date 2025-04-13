FROM python:3.13-bullseye

# Create a group and user
RUN groupadd -r handeesofficial && useradd -r -g handeesofficial handeesofficial

WORKDIR /home/handeesofficial/backend

RUN apt update && apt install nginx -y
COPY nginx/server.conf /etc/nginx/sites-available
RUN ln -s /etc/nginx/sites-available/server.conf /etc/nginx/sites-enabled/server.conf


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

COPY . .

EXPOSE 5000 5001

# CMD [ "/usr/local/bin/supervisord", "-c", "supervisord-dev.conf"]
# RUN [ "env/bin/supervisord", "-c", "supervisord-dev.conf"]
# CMD ["/usr/bin/bash", "-c", "sleep 3600"]

# CMD [ "env/bin/supervisorctl", "start", "nginx", "-c", "supervisord-dev.conf"]
CMD ["/bin/sh", "entrypoints/main_point.sh"]
