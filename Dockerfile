FROM python:3.5-alpine

COPY . /app
WORKDIR /app
RUN python setup.py install
ENTRYPOINT ["buildr"]
CMD ["--help"]
