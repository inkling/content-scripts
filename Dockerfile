

FROM python:2-alpine

RUN \
  apk update && apk upgrade && \
  apk --no-cache add git bash \
  ruby ruby-dev \
  make gcc libc-dev \
  libffi-dev && \
  gem install --no-document compass && \
  pip install --no-cache-dir beautifulsoup4 && \
  rm -rf /var/cache/apk/*

ADD . /usr/bin/inkling-rsync

ENV PATH=/usr/bin/inkling-rsync/bin:$PATH











