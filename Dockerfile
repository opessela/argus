FROM python:2-onbuild
ARG http_proxy
ARG https_proxy
COPY . /usr/src/app
WORKDIR /usr/src/app