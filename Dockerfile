FROM dimitri/pgloader:latest
LABEL maintainer="nathan@nathan-s.com"
LABEL url="https://github.com/Nathan-LS/Insight"
ARG PGLOADER_VERSION="master"
ENV PYTHONUNBUFFERED=1
ENV POSTGRES_HOST=""
ENV POSTGRES_PORT=5432
ENV POSTGRES_USER=""
ENV POSTGRES_PASSWORD=""
ENV POSTGRES_DB=""
ENV SQLITE_DB_PATH="Database.db"

RUN apt-get update && apt-get install -y \
 apt-utils \
 curl \
 ca-certificates \
 gnupg \
 lsb-release
RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
RUN curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

RUN apt-get update && apt-get install -y \
 python3 \
 python3-pip \
 sqlite3 \
 libpq-dev \
 postgresql-client-12
RUN rm -rf /var/lib/apt/lists/*

RUN mkdir /InsightMigratePython /app /home/insight
RUN addgroup -gid 1007 insight
RUN useradd --system --shell /bin/bash --home /app -u 1006 -g insight insight
RUN chown insight:insight /InsightMigratePython /app /home/insight
WORKDIR /InsightMigratePython
USER insight
COPY ./SQLiteToPostgresMigrate.py /InsightMigratePython/
COPY ./requirements.txt /InsightMigratePython/
USER root
RUN pip3 install wheel setuptools
RUN pip3 install --upgrade -r requirements.txt
USER insight
WORKDIR /app
ENTRYPOINT []
CMD ["python3", "/InsightMigratePython/SQLiteToPostgresMigrate.py"]

