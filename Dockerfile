FROM python:3.11.0a5-alpine3.15
MAINTAINER  Nick <linickx.com>
RUN pip install Flask pyyaml requests

COPY ise-exporter.py  /bin/ise-exporter
COPY ise.yml       /etc/ise-exporter/ise.yml

EXPOSE      9123
ENTRYPOINT  [ "/bin/ise-exporter" ]
