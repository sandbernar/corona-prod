<p align="center">
  <a href="https://github.com/thelastpolaris/anti-corona-crm/">
    <img src="web-app/app/main/static/assets/img/brand/blue.png" alt="Logo" width="400">
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

  ## Обновление проекта
```bash
$> cd path_to_project/web-app/
$> git pull
$> docker-compose down && docker-compose build && docker-compose up -d
```
