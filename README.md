<p align="center">
  <a href="https://github.com/thelastpolaris/anti-corona-crm/">
    <img src="web-app/app/base/static/assets/img/brand/blue.png" alt="Logo" width="400">
  </a>

  <h3 align="center">COVID-19 | Центр Контроля</h3>

  <p align="center">
    Web приложение, призванное помочь Минздраву РК контролировать распространение коронавируса
    <br />
  </p>
  
  ## Список Возможностей

* Загрузка списка новых пациентов из .xls и .xlsx файлов. Извлечение и сохранение данных о пациентах в базу данных
* Добавление новых пациентов через удобную веб-форму
* Онлайн карта, отображающая всех пациентов
* Поиск пациентов по регионам, статусам "найден" и "госпитализирован"
* Разработано с помощью Python, веб фреймворка Flask, и <a href="https://github.com/app-generator/flask-boilerplate-dashboard-argon">данного шаблона</a>

  ## Запуск
  ~~~~
  $ export CONFIG_MODE=(Debug/Production)
  $ export DATABASE_USER=*your PostgreSQL user*
  $ export DATABASE_PASSWORD=*your PostgreSQL user password*
  $ export DATABASE_HOST=*your PostgreSQL host (usually leave empty)*
  $ export DATABASE_PORT=*your PostgreSQL port (usually 5432)*  
  $ export DATABASE_NAME=*your PostgreSQL database name*
  $ cd web_app
  $ export FLASK_APP=run
  $ flask run --host 0.0.0.0 --port 5000
  ~~~~
 
  ## Онлайн Демо

* Онлайн демо доступно по адресу http://a6e061ca.ngrok.io (если демо не работает, пожалуйста, свяжитесь со мной)
* Зарегистрируйте новый аккаунт, либо воспользуйтесь тестовым (логин - test, пароль - test)
* На странице "Добавить Данные" попробуйте загрузить <a href="https://github.com/thelastpolaris/anti-corona-crm/blob/master/%D0%9F%D1%80%D0%B8%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D0%B5%201.%20%D0%A1%D0%BF%D0%B8%D1%81%D0%BE%D0%BA%20%D0%BF%D0%B0%D1%81%D1%81%D0%B0%D0%B6%D0%B8%D1%80%D0%BE%D0%B2%20(%D0%B7%D0%B0%D0%B3%D1%80%D1%83%D0%B7%D0%B8%D1%82%D0%B5%2C%20%D0%B4%D0%B5%D0%BC%D0%BE).xlsx">данный файл</a>
* Попробуйте добавить пациента вручную

  ## Локализация
* ``pybabel extract -F babel.cfg -k _l -o messages.pot .``
* ``pybabel init -i messages.pot -d app/translations -l '*your locale code (e.g. kk_KZ)*'``
* Используйте Poedit для перевода .po файла
* ``pybabel update -i messages.pot -d app/translations`` для обновления файла локализации


  ## Обо Мне
* Данный проект был разработан в рамках хакатона "anti-corona" от <a href="http://alem.school">alem.school</a>
* Команда Fight the Virus, я единственный ее участник. Мой E-Mail afedoskin3@gmail.com
* Заканчиваю магистратуру по Аналитике Данных в Университете Хильдесхайма (Германия). На данный момент нахожусь дома, в Шымкенте.

  ## Развертывание на сервере
Репозиторий содержит скрипт `setup.sh`. Данный скрипт устанавливает на сервере c ОС _Ubuntu 18.04_ зависимости этого проекта и запускает его.
1. Скрипт устанавливает на сервере: nginx, docker, docker-compose, postgresql.
2. Создает конфигурационный nginx файл.
3. Cоздает в postgresql UTF8 базу данных и пользователя.
4. Запускает проект.

Перед запуском следует указать следующие _env variables_:
```bash
$> export CRM_ENDPOINT="crm.yourwebsite.kz"
$> export DATABASE_USER="someuser"
$> export DATABASE_PASSWORD="somepassword"
```

Далее
```bash
$> sh setup.sh
```

  ## Перезапуск проекта
```bash
$> cd path_to_project/web-app/
$> docker-compose down && docker-compose up -d
```
