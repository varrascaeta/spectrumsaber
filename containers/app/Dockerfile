FROM python:3.12-slim-bullseye
SHELL ["/bin/bash", "-c"]
EXPOSE 8000
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get -y update
RUN apt-get -y upgrade

RUN mkdir /app
WORKDIR /app

COPY requirements/local.txt /app
RUN pip install -r local.txt
ENV PYTHONPATH="/:$PYTHONPATH"
RUN echo $PYTHONPATH
RUN echo $PWD

COPY . /app/
