docker exec -it postgres psql -U postgres -c "update pg_database set datistemplate=false where datname='template1';" && \
docker exec -it postgres psql -U postgres -c "drop database Template1;" && \
docker exec -it postgres psql -U postgres -c "create database template1 with owner=postgres encoding='UTF-8' lc_collate='en_US.utf8' lc_ctype='en_US.utf8' template template0;" && \
docker exec -it postgres psql -U postgres -c "update pg_database set datistemplate=true where datname='template1';" && \
docker exec -it postgres psql -U postgres -c "CREATE DATABASE anti_corona_crm WITH TEMPLATE = template1 ENCODING = 'UTF8';" && \
docker exec -it postgres psql -U postgres -c "CREATE ROLE ${DATABASE_USER} LOGIN SUPERUSER PASSWORD '${DATABASE_PASSWORD}'"
