ARG INSIGHT_TAG="latest"
FROM nathanls/insight:$INSIGHT_TAG

LABEL url="https://github.com/EVEInsight/InsightPostgresMigrator"
LABEL maintainer="maintainers@eveinsight.net"

ARG PGLOADER_VERSION="master"
ARG PGClient_VERSION="14"
ENV IntegrityCheckOnly="false"
ENV PerformIntegrityCheck="true"
ENV PYTHONUNBUFFERED=1
ENV POSTGRES_HOST=""
ENV POSTGRES_PORT=5432
ENV POSTGRES_USER=""
ENV POSTGRES_PASSWORD=""
ENV POSTGRES_DB=""
ENV SQLITE_DB="Database.db"
ENV INSIGHT_PATH="/InsightDocker/Insight/Insight"
ENV PGLOADER_BatchRows = 25000
ENV PGLOADER_BatchSize = "20 MB"
ENV PGLOADER_PrefetchRows = 100000
ENV PGLOADER_Workers = 4
ENV PGLOADER_Concurrency = 1
ENV PGLOADER_MaxParallelIndex = 6

#do not change
ENV DB_DRIVER="postgres"
ENV DISCORD_TOKEN="null"
ENV CCP_CLIENT_ID="null"
ENV CCP_SECRET_KEY="null"
ENV CCP_CALLBACK_URL="null"
ENV HEADERS_FROM_EMAIL="admin@eveinsight.net"
ENV PGLOADER_PATH="/opt/pgloader/build/bin/pgloader"

USER root
RUN rm -f /InsightDocker/sqlite-latest.sqlite
RUN apt-get update && apt-get install -y \
 sqlite3 \
 sbcl \
 unzip \
 libsqlite3-dev \
 make \
 curl \
 gawk \
 freetds-dev \
 libzip-dev \
 postgresql-client-$PGClient_VERSION
RUN rm -rf /var/lib/apt/lists/*

USER root
WORKDIR /opt
RUN git clone -b $PGLOADER_VERSION --single-branch https://github.com/dimitri/pgloader.git --depth 1
WORKDIR /opt/InsightMigrateTool
RUN chown -R insight:insight /opt/pgloader
USER insight
WORKDIR /opt/pgloader
RUN make pgloader

USER root
WORKDIR /opt/InsightMigrateTool
COPY ./InsightMigrateTool ./InsightMigrateTool
COPY ./requirements.txt ./
RUN chown -R insight:insight /opt/InsightMigrateTool
RUN find /opt/InsightMigrateTool -type f -exec chmod 0644 {} \;
USER insight
RUN pip3 install --upgrade -r requirements.txt
WORKDIR /app
ENTRYPOINT ["python3", "/opt/InsightMigrateTool/InsightMigrateTool/SQLiteToPostgresMigrate.py"]

