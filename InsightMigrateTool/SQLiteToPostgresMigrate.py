import psycopg2
import sqlite3
import os
import sys
import traceback
from distutils.version import LooseVersion
import subprocess
import datetime
from dateutil.parser import parse as dateTimeParser
import decimal
from psycopg2 import extras

REQUIRED_SQLITE_VERSION = LooseVersion("v2.6.0")
IntegrityCheckOnly = bool(os.getenv("IntegrityCheckOnly").lower() in ["true", "t"])
SQLITE_PATH = os.getenv("SQLITE_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
INSIGHT_PATH = os.getenv("INSIGHT_PATH")
PGLOADER_PATH = os.getenv("PGLOADER_PATH") if os.getenv("PGLOADER_PATH") is not None else "pgloader"
pg_connection_str = "postgresql://{}:{}@{}:{}/{}".format(POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST,
                                                         POSTGRES_PORT, POSTGRES_DB)
PGLOADER_BatchRows = os.getenv("PGLOADER_BatchRows")
PGLOADER_BatchSize = os.getenv("PGLOADER_BatchSize")
PGLOADER_PrefetchRows = os.getenv("PGLOADER_PrefetchRows")
PGLOADER_Workers = os.getenv("PGLOADER_Workers")
PGLOADER_Concurrency = os.getenv("PGLOADER_Concurrency")
PGLOADER_MaxParallelIndex = os.getenv("PGLOADER_MaxParallelIndex")

def dump_schema(schema_file):
    try:
        cmd = "pg_dump --dbname={} --schema-only --file {}".format(pg_connection_str, schema_file)
        r = subprocess.run(cmd, shell=True)
        if r.returncode != 0:
            print("Error - Got return code {} when attempting to dump the postgres schema.".format(r.returncode))
            sys.exit(1)
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        sys.exit(1)


def dict_factory(cursor, row):
# src https://docs.python.org/3/library/sqlite3.html row_factory
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def migration_check_integrity(table: str, sort_by: list):
    connection_sqlite = None
    connection_postgres = None
    query_count = "SELECT count(*) as count FROM {};".format(table)
    try:
        connection_sqlite = sqlite3.connect(SQLITE_PATH)
        connection_sqlite.row_factory = dict_factory
        cursor_sqlite = connection_sqlite.cursor()
        connection_postgres = psycopg2.connect(host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
                             user=POSTGRES_USER, password=POSTGRES_PASSWORD)
        cursor_postgres = connection_postgres.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor_sqlite.execute(query_count)
        cursor_postgres.execute(query_count)
        count_sqlite = cursor_sqlite.fetchone()
        count_postgres = cursor_postgres.fetchone()
        total_row_count = count_sqlite.get("count")
        print("Checking {} ({:,} total rows)...".format(table, total_row_count))
        if count_sqlite.get("count") != count_postgres.get("count"):
            print("Error: Rows in {} table do not match. Some data may be missing. SQLite: {} - Postgres: {}".format(table, count_sqlite, count_postgres))
            sys.exit(1)
        offset = 0
        ratio_print = .25
        while True:
            if offset >= total_row_count:
                break
            query_all = "SELECT * FROM {} order by {} limit 2000000 offset {};".format(table, ",".join(sort_by), offset)
            cursor_sqlite.execute(query_all)
            cursor_postgres.execute(query_all)
            while True:
                result_sqlite = cursor_sqlite.fetchone()
                result_postgres = cursor_postgres.fetchone()
                if result_sqlite is None or result_postgres is None:
                    if offset < total_row_count:
                        break
                    if offset != total_row_count:
                        print("Error final offset does not equal total row count.")
                        sys.exit(1)
                    break
                if total_row_count >= 1e6 and (offset >= (total_row_count * ratio_print)):
                    print("Completed {:,} row checks on table {}. {}% done".format(offset, table, int(ratio_print * 100)))
                    ratio_print += .25
                offset += 1
                if len(result_sqlite.keys()) != len(result_postgres.keys()):
                    print("Error - Missing column. SQLite: '{}' Postgres: '{}'".format(result_sqlite, result_postgres))
                    sys.exit(1)
                else:
                    for column_key in result_sqlite.keys():
                        item_sqlite = result_sqlite[column_key]
                        item_postgres = result_postgres[column_key]
                        if isinstance(item_sqlite, int) and isinstance(item_postgres, bool):
                            item_sqlite = bool(item_sqlite)
                        if isinstance(item_postgres, datetime.datetime):
                            item_postgres = item_postgres.timestamp()
                            item_sqlite = dateTimeParser(item_sqlite).timestamp()
                        if isinstance(item_sqlite, bytes):
                            item_postgres = bytes(item_postgres)
                        if (isinstance(item_sqlite, float) or isinstance(item_sqlite, int)) \
                                and isinstance(item_postgres, decimal.Decimal):
                            item_sqlite = float(item_sqlite)
                            item_postgres = float(item_postgres.normalize())
                        if (item_sqlite != item_postgres) or (type(item_sqlite) != type(item_postgres)):
                            print("Error - Row not copied successfully on column '{}'. SQLite: '{}' Postgres: '{}'".
                                  format(column_key, result_sqlite, result_postgres))
                            sys.exit(1)
                        else:
                            pass
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection_sqlite:
            connection_sqlite.close()
        if connection_postgres:
            connection_postgres.close()


def run_integrity_checks():
    print("Running integrity checks on data to ensure data copied successfully. This may take some time...")
    migration_check_integrity("alliances", ["alliance_id"])
    migration_check_integrity("categories", ["category_id"])
    migration_check_integrity("characters", ["character_id"])
    migration_check_integrity("constellations", ["constellation_id"])
    migration_check_integrity("contacts_alliances", ["alliance_id, token", "owner"])
    migration_check_integrity("contacts_characters", ["character_id", "token", "owner"])
    migration_check_integrity("contacts_corporations", ["corporation_id", "token", "owner"])
    migration_check_integrity("corporations", ["corporation_id"])
    migration_check_integrity("\"discord_capRadar\"", ["channel_id"])
    migration_check_integrity("discord_channels", ["channel_id"])
    migration_check_integrity("\"discord_enFeed\"", ["channel_id"])
    migration_check_integrity("discord_prefixes", ["server_id", "prefix='$'", "prefix='?'", "prefix='!'", "prefix"]) # postgres sorts some symbols in different order than sqlite
    migration_check_integrity("discord_servers", ["server_id"])
    migration_check_integrity("discord_tokens", ["channel_id", "token"])
    migration_check_integrity("discord_users", ["user_id"])
    migration_check_integrity("filter_alliances", ["channel_id", "filter_id"])
    migration_check_integrity("filter_categories", ["channel_id", "filter_id"])
    migration_check_integrity("filter_characters", ["channel_id", "filter_id"])
    migration_check_integrity("filter_constellations", ["channel_id", "filter_id"])
    migration_check_integrity("filter_corporations", ["channel_id", "filter_id"])
    migration_check_integrity("filter_groups", ["channel_id", "filter_id"])
    migration_check_integrity("filter_regions", ["channel_id", "filter_id"])
    migration_check_integrity("filter_systems", ["channel_id", "filter_id"])
    migration_check_integrity("filter_types", ["channel_id", "filter_id"])
    migration_check_integrity("groups", ["group_id"])
    migration_check_integrity("insight_meta", ["key"])
    migration_check_integrity("locations", ["location_id"])
    migration_check_integrity("regions", ["region_id"])
    migration_check_integrity("stargates", ["system_from", "system_to"])
    migration_check_integrity("systems", ["system_id"])
    migration_check_integrity("tmp_intjoin", ["no_pk"])
    migration_check_integrity("tmp_strjoin", ["no_pk"])
    migration_check_integrity("tokens", ["token_id"])
    migration_check_integrity("types", ["type_id"])
    migration_check_integrity("version", ["row"])
    migration_check_integrity("victims", ["kill_id"])
    migration_check_integrity("kills", ["kill_id"])
    migration_check_integrity("attackers", ["no_pk"])
    print("All tables verified ok. Data from sqlite mirrors the postgres database.")


def sqlite_remediation(table):
    connection = None
    sql_query_delete = "DELETE FROM {} WHERE channel_id not in (SELECT channel_id FROM discord_channels)".format(table)
    sql_query_select = "SELECT * FROM {} WHERE channel_id not in (SELECT channel_id FROM discord_channels)".format(table)
    try:
        connection = sqlite3.connect(SQLITE_PATH)
        c = connection.cursor()
        c.execute(sql_query_select)
        for r in c.fetchall():
            print("Deleting from '{}' row as the foreign key constraint fails - {}".format(table, r))
        c.execute(sql_query_delete)
        connection.commit()
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection:
            connection.close()

def sqlite_remediate_query(q):
    connection = None
    try:
        connection = sqlite3.connect(SQLITE_PATH)
        c = connection.cursor()
        c.execute(q)
        connection.commit()
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection:
            connection.close()


def sqlite_apply_remediations():
    print("Applying remediation to SQLite before migration...")
    sqlite_remediation("filter_alliances")
    sqlite_remediation("filter_categories")
    sqlite_remediation("filter_characters")
    sqlite_remediation("filter_constellations")
    sqlite_remediation("filter_corporations")
    sqlite_remediation("filter_groups")
    sqlite_remediation("filter_regions")
    sqlite_remediation("filter_systems")
    sqlite_remediation("filter_types")
    sqlite_remediate_query("UPDATE \"discord_capRadar\" SET max_km_age = 2000000000 where max_km_age > 2000000000;")


def cast_rules():
    yield "type integer to integer using integer-to-string"


def get_cast_rules():
    rules = ""
    for r in list(cast_rules()):
        rules += "--cast \"{}\" ".format(r)
    return rules.strip()

def check_sqlite_db_version():
    print("Checking the current SQLITE DB version...")
    if not SQLITE_PATH:
        print("SQLITE 'SQLITE_DB_PATH' var is not set. Exiting.")
        sys.exit(1)
    if not os.path.exists(SQLITE_PATH):
        print("'{}' does not exist. Exiting...".format(SQLITE_PATH))
        sys.exit(1)
    connection = None
    try:
        connection = sqlite3.connect(SQLITE_PATH)
        c = connection.cursor()
        result = c.execute("SELECT database_version FROM version WHERE version.row=0")
        r = result.fetchone()
        current_version = LooseVersion(r[0])
        if REQUIRED_SQLITE_VERSION > current_version:
            print("The Insight sqlite database must be upgraded to '{}' before the migration occurs. "
                  "The current version is {}. Please start Insight with the 'sqlite3' DB driver to upgrade the "
                  "database first before migrating.".format(REQUIRED_SQLITE_VERSION, current_version))
            sys.exit(1)
        else:
            print("Pre-migration patches are applied to SQLITE database. Safe to upgrade.")
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection:
            connection.close()


def import_insight_schema():
    print("Importing Insight schema to target database...")
    try:
        cmd = "python3 {} --schema-import".format(INSIGHT_PATH)
        r = subprocess.run(cmd, shell=True)
        if r.returncode == 0:
            print("{} - Success importing the Insight schema!".format(datetime.datetime.utcnow()))
        else:
            print("{} - Error when importing Insight schema. Exit code: {}".format(datetime.datetime.utcnow(), r.returncode))
            sys.exit(1)
    except Exception as ex:
        print(ex)
        sys.exit(1)


def check_postgres_db():
    print("Checking postgres database for migration...")
    c = None
    try:
        c = psycopg2.connect(host=POSTGRES_HOST, port=POSTGRES_PORT, dbname=POSTGRES_DB,
                                      user=POSTGRES_USER, password=POSTGRES_PASSWORD)
        cursor = c.cursor()
        cursor.execute("SELECT count(*) FROM information_schema.tables where table_schema = 'public'")
        r = cursor.fetchone()
        table_count = int(r[0])
        if table_count > 0:
            print("Error - The destination database is not empty. You can only migrate to an empty database. No changes were made.")
            sys.exit(1)
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        sys.exit(1)
    finally:
        if c:
            c.close()


def check_summary(log_file: str):
    import_error_detected = False
    with open(log_file) as f:
        error_column_start = None
        error_column_end = None
        for l in f.readlines():
            print(l.strip("\n"))
            if not error_column_start and not error_column_end:
                find_str = "errors"
                error_column_start = l.find(find_str)
                error_column_end = error_column_start + len(find_str)
                if error_column_start <= 0:
                    print("Error parsing summary table.")
                    sys.exit(1)
                else:
                    continue
            error_line = l[error_column_start:error_column_end]
            try:
                error_count = int(error_line.strip())
                if error_count > 0:
                    import_error_detected = True
            except ValueError:
                continue
    if import_error_detected:
        print("\nErrors on import detected. The imported postgres database may be missing critical items. "
              "Please drop the postgres database and rerun this script.")
        sys.exit(1)
    else:
        print("\nDatabase migrate summary reports no errors.")


def run_migration(log_file: str):
    print("Running migration from SQLite to Postgres. The summary log is located at {}. "
          "This may take some time...".format(log_file))
    try:
        cmd = '{} --on-error-stop --summary {} ' \
              '--with "batch rows = {}" --with "batch size = {}" --with "prefetch rows = {}" ' \
              '--with "workers = {}" --with "concurrency = {}" --with "max parallel create index = {}" ' \
              '--with "data only" --with "truncate" --with "create no tables" --with "include no drop" ' \
              '--with "create no indexes" --with "drop indexes" --with "on error stop" --with "reset sequences" ' \
              '--with "quote identifiers" --set "client_min_messages = \'error\'" ' \
              '{} ' \
              '{} {}'.format(PGLOADER_PATH, log_file, PGLOADER_BatchRows, PGLOADER_BatchSize, PGLOADER_PrefetchRows,
                             PGLOADER_Workers, PGLOADER_Concurrency, PGLOADER_MaxParallelIndex, get_cast_rules(),
                             SQLITE_PATH, pg_connection_str)
        r = subprocess.run(cmd, shell=True)
        if r.returncode == 0:
            print("{} - Success migrating the database!".format(datetime.datetime.utcnow()))
        else:
            print("{} - Error when running pgloader. Exit code: {}".format(datetime.datetime.utcnow(), r.returncode))
            sys.exit(1)
    except Exception as ex:
        print(ex)


def main():
    start_time = datetime.datetime.utcnow()
    t = datetime.datetime.utcnow().strftime("%d-%m-Y-%H%M%S")
    check_sqlite_db_version()
    check_postgres_db()
    if not IntegrityCheckOnly:
        import_insight_schema()
        sqlite_apply_remediations()
        dump_schema("/app/schema_preimport_{}.sql".format(t))
        log_file = "/app/postgres_migrate_{}.log".format(t)
        run_migration(log_file)
        dump_schema("/app/schema_postimport_{}.sql".format(t))
        check_summary(log_file)
    else:
        print("Running database integrity checks only.")
    run_integrity_checks()
    total_seconds = (datetime.datetime.utcnow() - start_time).total_seconds()
    print("Success! All data was successfully copied to postgres! You may start using the newly migrated "
          "postgres database with Insight!\n\nTotal time taken: {}s".format(total_seconds))


if __name__ == "__main__":
    main()


