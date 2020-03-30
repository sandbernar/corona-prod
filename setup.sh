#!/usr/bin/env bash

# check if env variables are set

if [[ -z "${CRM_ENDPOINT}" ]]; then
  echo "NO CRM_ENDPOINT env variable"
  exit 1
fi

if [[ -z "${DATABASE_USER}" ]]; then
  echo "NO DATABASE_USER env variable"
  exit 1
fi

if [[ -z "${DATABASE_PASSWORD}" ]]; then
  echo "NO DATABASE_PASSWORD env variable"
  exit 1
fi

# exit immediately if a command exits with a non-zero status.
set -e

# print commands and their arguments as they are executed.
set -x

sudo apt update

# install nginx
sudo apt install nginx
sudo ufw allow 'Nginx Full'

# setup nginx configuration for CRM endpoint
cat <<EOF >/etc/nginx/sites-available/CRM.conf
upstream crm {
    server localhost:5005;
}
server {
    server_name ${CRM_ENDPOINT};
    location / {
        proxy_pass  http://crm;
        proxy_redirect     off;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host $server_name;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 950s;
    }
}
EOF
sudo ln -s /etc/nginx/sites-available/CRM.conf /etc/nginx/sites-enabled/CRM.conf
sudo service nginx reload

# install docker
sudo apt install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
sudo apt update
sudo apt install docker-ce
sudo usermod -aG docker ${USER}
su - ${USER}

# docker-compose
sudo curl -L https://github.com/docker/compose/releases/download/1.21.2/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# install postgres
sudo apt install postgresql postgresql-contrib

# create database
sudo -i -u postgres psql -c "update pg_database set datistemplate=false where datname='template1';"
sudo -i -u postgres psql -c "drop database Template1;"
sudo -i -u postgres psql -c "create database template1 with owner=postgres encoding='UTF-8' lc_collate='en_US.utf8' lc_ctype='en_US.utf8' template template0;"
sudo -i -u postgres psql -c "update pg_database set datistemplate=true where datname='template1';"
sudo -i -u postgres psql -c "CREATE DATABASE anti_corona_crm WITH TEMPLATE = template1 ENCODING = 'UTF8';"

# create user with password
sudo -i -u postgres psql -c "CREATE ROLE ${DATABASE_USER} LOGIN SUPERUSER PASSWORD '${DATABASE_PASSWORD}'"

# setup CRM
git clone github.com/thelastpolaris/anti-corona-crm ~/anti-corona-crm
touch ~/anti-corona-crm/web-app/.env

cat <<EOF >~/anti-corona-crm/web-app/.env
CONFIG_MODE=Production
DATABASE_USER=${DATABASE_USER}
DATABASE_PASSWORD=${DATABASE_PASSWORD}
DATABASE_NAME=anti_corona_crm
DATABASE_HOST=localhost
DATABASE_PORT=5432
EOF

# run CRM
docker-compose -f ~/anti-corona-crm/web-app/docker-compose.yml up -d
