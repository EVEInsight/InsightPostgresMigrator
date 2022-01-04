# InsightPostgresMigrator
[![](https://img.shields.io/badge/-EVEInsight.net-154360)](https://eveinsight.net)
[![](https://img.shields.io/docker/pulls/nathanls/insightpostgresmigrator.svg)](https://hub.docker.com/r/nathanls/insightpostgresmigrator)
[![](https://img.shields.io/github/license/EVEInsight/InsightPostgresMigrator.svg)](https://github.com/EVEInsight/InsightPostgresMigrator/blob/master/LICENSE)
[![](https://img.shields.io/discord/379777846144532480.svg)](https://discord.eveinsight.net)
[![](https://img.shields.io/badge/-Wiki-blueviolet)](https://wiki.eveinsight.net)

Migrates a SQLite installation of [Insight](https://git.eveinsight.net) to Postgres using pgloader and additional integrity checking scripts.

# Quick reference
* **Where to get help:**

    [Insight Discord support server](https://discord.eveinsight.net/)
* **Where to file issues:**
    
    [https://github.com/EVEInsight/InsightPostgresMigrator/issues](https://github.com/EVEInsight/InsightPostgresMigrator/issues)

# Supported tags and ```Dockerfile``` links
* [```latest```](https://github.com/EVEInsight/InsightPostgresMigrator/blob/master/Dockerfile)
* [```development```](https://github.com/EVEInsight/InsightPostgresMigrator/blob/master/Dockerfile)

# What is Insight?
Insight provides [EVE Online](https://www.eveonline.com/) killmail streaming and utility commands for Discord. Insight can stream personal or corporate killboards, detect supercapitals with a proximity radar, estimate ship composition from local chat scans, and more!
Killmails and intel are presented in Discord rich embeds containing relevant links and images to quickly identify important information.

# What is InsightPostgresMigrator?
This container migrates a SQLite Insight database to PostgreSQL. It copies and verifies data into an empty PostgreSQL database.

# How to use this image
## Start a migration instance via ```docker run```
First, ensure you have an empty PostgreSQL database with a user that has access. Ensure there are no active writes or reads to the SQLite database (stop the bot).

The following command runs the migration tool against the current directory containing a SQLite Insight database file (Database.db):
```
$ docker run -it --rm -v ${PWD}:/app -e POSTGRES_HOST="host" -e POSTGRES_USER="user" -e POSTGRES_PASSWORD="pass" -e POSTGRES_DB="dbname" nathanls/insightpostgresmigrator
```
.. where ```host```, ```user```, ```pass```, ```dbname``` are to be replaced with your PostgreSQL details.

Adjust your mount from ```${PWD}``` as needed to mount the directory containing the Insight Docker volume.

Check exit codes and command output to ensure the migration is successful. 
Once that migration is successful you can adjust your Insight container to point to the new Postgres database through adjusting the ```DB_DRIVER``` and additional [environmental variables](https://wiki.eveinsight.net/en/install/EnvironmentVariables).

## ...via ```docker stack deploy``` or ```docker-compose```
Example ```stack.yml``` for ```InsightPostgresMigrator```:
```text
version: '3.1'
services:
  insightmigrate:
    image: nathanls/insightpostgresmigrator
    deploy:
      restart_policy:
        condition: none
    environment:
      POSTGRES_HOST: "db"
      POSTGRES_USER: "insightuser"
      POSTGRES_PASSWORD: "insightpass"
      POSTGRES_DB: "insightdb"
    volumes:
      - /Path/To/InsightVolume:/app
  db:
    image: postgres:14.1
    deploy:
      restart_policy:
        condition: always
    environment:
      POSTGRES_USER: "insightuser"
      POSTGRES_PASSWORD: "insightpass"
      POSTGRES_DB: "insightdb"
    volumes:
      - /Path/To/PostgresVolume:/var/lib/postgresql/data
```
# Environment Variables

### ```POSTGRES_HOST```
The DNS hostname of the Postgres cluster migration target.

### ```POSTGRES_USER```
The target postgres user that has read/write access to the database.

### ```POSTGRES_PASSWORD```
The target postgres user password.

### ```POSTGRES_DB```
The target database name residing on ```POSTGRES_HOST```.

### ```POSTGRES_PORT```
The target database port. Defaults to ```5432```.

### ```SQLITE_DB```
The source SQLite database file name. Defaults to ```Database.db```

### ```IntegrityCheckOnly```
Perform an integrity check only. Does not copy data into the postgres database.
Defaults to ```false```.

### ```PerformIntegrityCheck```
Perform a row difference check between both databases after migrating data. 
A large SQLite database (10GB+) can take 2 to 3 hours to fully check all rows with this option enabled.
Defaults to ```true```.

# Image Variants
The ```nathanls/insightpostgresmigrator``` container has multiple tags.

## ```nathanls/insightpostgresmigrator:latest```
The standard defacto image which imports the SQL schema from the [Insight master branch](https://github.com/EVEInsight/Insight/tree/master) into the empty Postgres database before copying data.

This should be the image used in most cases.

## ```nathanls/insightpostgresmigrator:development```
Image that imports the SQL schema from the [Insight development branch](https://github.com/EVEInsight/Insight/tree/development) into the empty Postgres database before copying data.

If you run the development version of Insight you should choose this image.

# License
View license for [Insight](https://github.com/EVEInsight/Insight/blob/master/LICENSE.md) and [InsightPostgresMigrator](https://github.com/EVEInsight/InsightPostgresMigrator/blob/master/LICENSE).

This container builds and makes use of [pgloader](https://github.com/dimitri/pgloader) with its own [license](https://github.com/dimitri/pgloader/blob/master/LICENSE).

## CCP Copyright Notice
EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights are reserved worldwide. All other trademarks are the property of their respective owners. EVE Online, the EVE logo, EVE and all associated logos and designs are the intellectual property of CCP hf. All artwork, screenshots, characters, vehicles, storylines, world facts or other recognizable features of the intellectual property relating to these trademarks are likewise the intellectual property of CCP hf. 

CCP hf. has granted permission to **Insight** to use EVE Online and all associated logos and designs for promotional and information purposes on its website but does not endorse, and is not in any way affiliated with, **Insight**. CCP is in no way responsible for the content on or functioning of this website, nor can it be liable for any damage arising from the use of this website.