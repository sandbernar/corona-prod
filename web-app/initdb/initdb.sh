#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
    update pg_database set datistemplate=false where datname='template1';
    drop database Template1;
    create database template1 with owner=postgres encoding='UTF-8' lc_collate='en_US.utf8' lc_ctype='en_US.utf8' template template0;
    update pg_database set datistemplate=true where datname='template1';
    CREATE DATABASE anti_corona_crm WITH TEMPLATE = template1 ENCODING = 'UTF8';
    CREATE ROLE ${DATABASE_USER} LOGIN SUPERUSER PASSWORD '${DATABASE_PASSWORD}';
EOSQL