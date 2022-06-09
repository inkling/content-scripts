FROM python:2

RUN apt-get -y update && \
  apt-get install -y ruby-full gcc && \
  gem install --no-document compass && \
  pip install --no-cache-dir beautifulsoup4 && \
  apt-get clean

ADD . /usr/bin/inkling-rsync

ENV PATH=/usr/bin/inkling-rsync/bin:$PATH
ENV PYTHONPATH=/usr/bin/inkling-rsync

RUN ["chmod", "+x", "/usr/bin/inkling-rsync/set-credentials.sh"]









