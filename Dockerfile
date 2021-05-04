FROM python:3.9-slim

# https://dev.splunk.com/enterprise/docs/developapps/testvalidate/appinspect/splunkappinspectclitool/installappinspect/installappinspectonlinux

RUN apt-get update && \
    apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    lib32z1-dev \
    python-lxml \
    libmagic-dev

RUN pip install --upgrade pip && \
    pip install splunk-appinspect

WORKDIR /app

COPY . .

CMD splunk-appinspect inspect ./src
