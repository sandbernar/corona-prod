## Запуск

Запустится на порту :5005

```bash
docker-compose up -d
```

## Запуск на Mac

На MacOS `--network=host` для Docker не работает. Данный функционал поддерживается исключительно на ОС Linux.

Поэтому чтобы локально запустить у себя на Mac, следуйте следующим инструкциям.

Эти инструкции запустят изолированные в контейнерах _данное приложение_ и базу данных _PostgreSQL_.

Создаем сеть `postgres` в котором будут коммуницировать наши сервисы
```bash
docker network create --driver bridge postgres
```

Запускаем PostreSQL контейнер, указывая сеть флагом `--network=postgres`. Для сохранения данных между перезапусками базы данных
указан флан `-v mount:/var/lib/postgresql/data`, который сохраняет данные в локальную папку `mount`. Поэтому убедидетесь создать 
эту папку перед запуском.
```bash
docker run -d \
    --network=postgres \
    -p 5432:5432 \
    --name postgres \
    -e POSTGRES_PASSWORD=YOUR_LOCAL_PSQL_PASSWORD \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v mount:/var/lib/postgresql/data \
    postgres
```

Теперь нужно настроить базу данных для работы с проектом: создать UTF-8 базу данных `anti_corona_ctm` и пользователя который будет 
обращаться к этой базе. Их данные далее сохраним в файле `.env`. Создайте перемененные окружения `DATABASE_USER` и `DATABASE_PASSWORD`.
```bash
docker exec -it postgres psql -U postgres -c "update pg_database set datistemplate=false where datname='template1';" && \
docker exec -it postgres psql -U postgres -c "drop database Template1;" && \
docker exec -it postgres psql -U postgres -c "create database template1 with owner=postgres encoding='UTF-8' lc_collate='en_US.utf8' lc_ctype='en_US.utf8' template template0;" && \
docker exec -it postgres psql -U postgres -c "update pg_database set datistemplate=true where datname='template1';" && \
docker exec -it postgres psql -U postgres -c "CREATE DATABASE anti_corona_crm WITH TEMPLATE = template1 ENCODING = 'UTF8';" && \
docker exec -it postgres psql -U postgres -c "CREATE ROLE ${DATABASE_USER} LOGIN SUPERUSER PASSWORD '${DATABASE_PASSWORD}'"
```

Сохраним эти данные в .env
```bash
cat <<EOF >~/anti-corona-crm/web-app/.env
CONFIG_MODE=Production
DATABASE_USER=${DATABASE_USER}
DATABASE_PASSWORD=${DATABASE_PASSWORD}
DATABASE_NAME=anti_corona_crm
DATABASE_HOST=postgres
DATABASE_PORT=5432
EOF
```

Запускаем проект указывая файл `docker-compose-mac.yml`. Этот файл запускает контейнер в сети `postgres`
```bash
docker-compose -f docker-compose-mac.yml up -d
```

Build проека
```bash
docker-compose -f docker-compose-mac.yml build
```

Перезапуск проекта
```bash
docker-compose -f docker-compose-mac.yml down && docker-compose -f docker-compose-mac.yml up -d
```
