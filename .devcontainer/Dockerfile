FROM mcr.microsoft.com/devcontainers/python:3

COPY . ./

RUN python -m pip install --upgrade pip \
    && python setup.py install
