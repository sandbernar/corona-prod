#!/bin/bash

docker stop postgres
docker stop web-app_appseed-app_1
docker rm postgres
docker rm web-app_appseed-app_1

docker run -d \
    --network=postgres \
    -p 5432:5432 \
    --name postgres \
    -e POSTGRES_PASSWORD=paswd \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v mount:/var/lib/postgresql/data \
    postgres

docker exec -it postgres psql -U postgres -c "drop database anti_corona_crm;"
docker exec -it postgres psql -U postgres -c "drop role adm;;"

docker exec -it postgres psql -U postgres -c "update pg_database set datistemplate=false where datname='template1';" && \
docker exec -it postgres psql -U postgres -c "drop database Template1;" && \
docker exec -it postgres psql -U postgres -c "create database template1 with owner=postgres encoding='UTF-8' lc_collate='en_US.utf8' lc_ctype='en_US.utf8' template template0;" && \
docker exec -it postgres psql -U postgres -c "update pg_database set datistemplate=true where datname='template1';" && \
docker exec -it postgres psql -U postgres -c "CREATE DATABASE anti_corona_crm WITH TEMPLATE = template1 ENCODING = 'UTF8';" && \
docker exec -it postgres psql -U postgres -c "CREATE ROLE ${DATABASE_USER} LOGIN SUPERUSER PASSWORD '${DATABASE_PASSWORD}'"

docker-compose -f docker-compose-mac.yml up -d

