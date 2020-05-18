# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request, Response
from flask_login import login_required, current_user
from app import login_manager, db

import pandas as pd
import io

from app.main.models import Region
from app.main.patients.models import Patient, PatientState, State
from app.main.various.forms import DownloadVariousData
from app.main.forms import TableSearchForm
import math
from app.login.models import User
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields, parse_date
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc, extract, func
from sqlalchemy.sql import select
import urllib
from datetime import datetime, timedelta

from app.main.users.modules import UserTableModule, UserPatientsTableModule

@blueprint.route('/export_various_data_xls', methods=['POST'])
@login_required
def export_various_data_xls():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500
    
    q = Patient.query
    
    infected_state_id = State.query.filter_by(value=c.state_infec[0]).first().id

    q = q.join(PatientState, PatientState.patient_id == Patient.id)
    q = q.filter(PatientState.state_id == infected_state_id)
    q = q.group_by(Patient.id)

    data = []

    def get_age_filter(age_start, age_end):
        date_start = datetime.today() - timedelta(days=age_start*365)
        date_end = datetime.today() - timedelta(days=age_end*365)

        return Patient.dob.between(date_start, date_end)

    for region in Region.query.all():
        if region.name != "Вне РК":
            infected_count = q.filter(Patient.region_id == region.id).count()

            entry = [region.name, infected_count]
            
            for age_range in [(0, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69)
                              , (70, 79), (80, 89), (90, 99)]:
                entry.append(q.filter(get_age_filter(age_range[0], age_range[1])).count())


            data.append(entry)

    data = pd.DataFrame(data, columns=[_("Регион"), _("Общее Число Инфицированных"), _("0-9"), _("10-19"),
                                       _("20-29"), _("30-39"), _("40-49"), _("50-59"), _("60-69"), _("70-79"),
                                       _("80-89"), _("90-99")])

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    data.to_excel(writer, index=False)

    def get_col_widths(df):
        widths = []
        for col in df.columns:
            col_data_width = max(df[col].map(str).map(len).max(), len(col))
            col_data_width *= 1.2

            widths.append(col_data_width)
        
        return widths

    for i, width in enumerate(get_col_widths(data)):
        writer.sheets['Sheet1'].set_column(i, i, width)

    writer.save()
    xlsx_data = output.getvalue()

    # region_name = Region.query.filter_by(id = region_id).first().name if region_id != -1 else c.all_regions
    filename_xls = "{}".format(_("пользователи"))

    filename_xls = "{}.xls".format(filename_xls)
    
    response = Response(xlsx_data, mimetype="application/vnd.ms-excel")
    response.headers["Content-Disposition"] = \
        "attachment;" \
        "filename*=UTF-8''{}".format(urllib.parse.quote(filename_xls.encode('utf-8')))

    return response

def download_xls(self):
        data = []

        for row in self.q.all():
            gender = _("Неизвестно")
            if row.gender != None:
                gender = _("Женский") if row.gender == True else _("Мужской")

            # contacted_id = [c.infected_patient_id for c in ContactedPersons.query.filter_by(contacted_patient_id=row.id).all()]
            # contacted_bool = _("Да") if len(contacted_id) else _("Нет")
            user_created = User.query.filter_by(id=row.created_by_id).first()
            user_organization = "" if not user_created else user_created.organization
            username = "" if not user_created else user_created.username

            # travel_date = ""
            # travel_info = ""

            # if row.travel_type:
            #     if row.travel_type.value == c.flight_type[0]:
            #         flight_travel = FlightTravel.query.filter_by(patient_id=row.id)
            #         if flight_travel.count():
            #             flight_travel = flight_travel.first()
            #             travel_date = flight_travel.flight_code.date
            #             travel_info = flight_travel.flight_code.code
            #     elif row.travel_type.value == c.train_type[0]:
            #         train_travel = TrainTravel.query.filter_by(patient_id=row.id)
            #         if train_travel.count():
            #             train_travel = train_travel.first()
            #             train = train_travel.train

            #             travel_date = train.arrival_date
            #             travel_info = "{}, {} - {},{}".format(train.from_country, train.from_city,
            #                                                   train.to_country, train.to_city)
            #     elif row.travel_type.value in c.various_travel_types_values:
            #         various_travel = VariousTravel.query.filter_by(patient_id=row.id)
            #         if various_travel.count():
            #             various_travel = various_travel.first()

            #             travel_date = various_travel.date
            #             travel_info = various_travel.border_control
            #     elif row.travel_type.value == c.blockpost_type[0]:
            #         blockpost_travel = BlockpostTravel.query.filter_by(patient_id=row.id)
            #         if blockpost_travel.count():
            #             blockpost_travel = blockpost_travel.first()

            #             travel_date = blockpost_travel.date
            #             travel_info = str(blockpost_travel.region)

            is_infected = yes_no(row.is_infected)
            is_found = yes_no(row.is_found)

            data.append([row.id, str(row), row.iin, gender, row.dob, str(row.region), 
                        row.pass_num, str(row.citizenship), str(row.country_of_residence),
                        str(row.travel_type), #travel_date, travel_info,
                        str(row.home_address), row.telephone, row.email, str(row.status),
                        is_found, is_infected, row.hospital,
                        row.job, row.job_position, row.job_category, row.job_address,
                        # contacted_bool, contacted_id,
                        row.created_date.strftime("%d-%m-%Y %H:%M"), user_organization, username])

        data = pd.DataFrame(data, columns=[_("ID"), _("ФИО"), _("ИИН"), _("Пол"), _("Дата Рождения"), _("Регион"),
                                           _("Номер Паспорта"), _("Гражданство"), _("Страна Проживания"),
                                           _("Тип Въезда"), #_("Дата Въезда"), _("Инфо о Въезде"),
                                           _("Домашний Адрес"), _("Телефон"), _("E-Mail"), _("Статус"),
                                           _("Найден"), _("Инфицирован"), _("Госпиталь"),
                                           _("Место Работы/Учебы"), _("Должность"), _("Категория Работы"),
                                           _("Адрес Работы"),
                                           #_("Контактный?"), _("Нулевой Пациент ID (Контакт)"),
                                           _("Дата Создания"), _("Организация"), _("Логин Специалиста")])

        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        data.to_excel(writer, index=False)

        def get_col_widths(df):
            widths = []
            for col in df.columns:
                col_data_width = max(df[col].map(str).map(len).max(), len(col))
                col_data_width *= 1.2

                widths.append(col_data_width)
            
            return widths

        for i, width in enumerate(get_col_widths(data)):
            writer.sheets['Sheet1'].set_column(i, i, width)

        writer.save()
        xlsx_data = output.getvalue()

        region_id = int(request.args.get("region_id", -1))
        region_name = c.all_regions
        
        region_query = Region.query.filter_by(id = region_id)
        if region_query.count():
            region_name = region_query.first().name

        filename_xls = "{}_{}".format(_("пациенты"), region_name)

        date_range_start = request.args.get("date_range_start", None)
        if date_range_start:
            filename_xls = "{}_{}".format(filename_xls, date_range_start)

        date_range_end = request.args.get("date_range_end", None)
        if date_range_end:
            filename_xls = "{}_{}".format(filename_xls, date_range_end)

        filename_xls = "{}.xls".format(filename_xls)
        
        response = Response(xlsx_data, mimetype="application/vnd.ms-excel")
        response.headers["Content-Disposition"] = \
            "attachment;" \
            "filename*=UTF-8''{}".format(urllib.parse.quote(filename_xls.encode('utf-8')))

        return response

@blueprint.route('/various', methods=['GET'])
@login_required
def various():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500

    form = DownloadVariousData()

    change = None
    error_msg = None

    return route_template('various/various', form=form, change=change, error_msg=error_msg)
#     form = UserActivityReportForm()

#     regions = get_regions(current_user)

#     if not form.region_id.choices:
#         form.region_id.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]
   


#     if "added_user" in request.args:
#         change =_("Пользователь был успешно добавлен")
#     elif "delete_user" in request.args:
#         change =_("Пользователь был успешно удален")
#     elif "error" in request.args:
#         error_msg = request.args["error"]

#     users_search_form = UserSearchForm()

#     if not users_search_form.region_id.choices:
#         users_search_form.region_id.choices = [(-2, _("Неважно"))]
#         users_search_form.region_id.choices += get_regions_choices(current_user)

#     q_patient = db.session.query(Patient.created_by_id,
#                                     func.count('*').label('patient_count'))    
    
#     q_patient = q_patient.group_by(Patient.created_by_id).subquery()
#     q = db.session.query(User, q_patient.c.patient_count).outerjoin(q_patient, User.id == q_patient.c.created_by_id)
    
#     users_table = UserTableModule(request, q, users_search_form, 
#         header_button=[(_("Добавить Пользователя"), "add_user")])

#     users_search_form.process()
#     form.process()
#     return route_template('users/users', users=users, users_table = users_table, form=form,
#                             users_search_form=users_search_form, constants=c, change=change, error_msg=error_msg)

# @blueprint.route('/add_user', methods=['GET', 'POST'])
# def add_user():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login_blueprint.login'))

#     if not current_user.is_admin:
#         return render_template('errors/error-500.html'), 500

#     form = CreateUserForm()

#     if not form.region_id.choices:
#         form.region_id.choices = get_regions_choices(current_user)

#     form.process()

#     if 'create' in request.form:
#         new_dict = request.form.to_dict(flat=True)
        
#         user = User.query.filter_by(username=new_dict['username']).first()
#         if user:
#             return route_template( 'users/add_user', error_msg=_('Имя пользователя уже зарегистрировано'), form=form, change=None)

#         if "is_admin" in new_dict:
#             new_dict["is_admin"] = int(new_dict["is_admin"]) == 1

#         if 'region_id' in new_dict:
#             if new_dict['region_id'] == '-1':
#                 new_dict['region_id'] = None

#         user = User(**new_dict)
        
#         db.session.add(user)
#         db.session.commit()

#         return redirect("{}?added_user".format(url_for('main_blueprint.users')))
#     else:
#         return route_template( 'users/add_user_and_profile', form=form, change=None, error_msg=None, is_profile=False)


# @blueprint.route('/user_profile', methods=['GET', 'POST'])
# @login_required
# def user_profile():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login_blueprint.login'))

#     if "id" in request.args:
#         if request.args["id"] != str(current_user.id):
#             if not current_user.is_admin:
#                 return render_template('errors/error-500.html'), 500

#         try:
#             user_query = User.query.filter_by(id=request.args["id"])
#             user = user_query.first()
#         except exc.SQLAlchemyError:
#             return render_template('errors/error-400.html'), 400    
        
#         if not user:
#             return render_template('errors/error-404.html'), 404
#         else:
#             form = UpdateUserForm()
            
#             change = None
#             error_msg = None

#             if not current_user.is_admin:
#                 form_fields = ["full_name", "username", "email", "region_id",
#                                 "telephone", "organization", "is_admin"]

#                 disable_form_fields(form, form_fields)
                                
#             if 'update' in request.form:
#                 values = request.form.to_dict()

#                 if current_user.is_admin:
#                     if 'username' in values:
#                         new_username = values['username']
                        
#                         if not new_username == user.username:
#                             if not User.query.filter_by(username = new_username).count():
#                                 user.username = new_username
#                             else:
#                                 error_msg = _("Пользователь с таким логином уже существует")

#                     if 'region_id' in values:
#                         if values['region_id'] == '-1':
#                             values['region_id'] = None

#                     if 'is_admin' in values:
#                         values['is_admin'] = int(values['is_admin']) == 1
#                 else:
#                     # Delete values that we don't update
#                     values.pop("is_admin", None)
#                     values.pop("username", None)
#                     values.pop("region_id", None)

#                 if not error_msg:
#                     if values.get('password', ''):
#                         password = values['password']

#                         user.password = hash_pass(password)

#                     values.pop("password", None)
#                     values.pop("csrf_token", None)
#                     values.pop("update", None)
                    
#                     user_query.update(values)

#                     db.session.add(user)
#                     db.session.commit()

#                     change = _("Данные обновлены")
            
#             user = user_query.first()
#             user_parameters = user.__dict__.copy()

#             user_parameters.pop("password", None)

#             populate_form(form, user_parameters)
#             form.region_id.choices = get_regions_choices(current_user)
  
#             form.process()

#             user_patients_search_form = UserPatientsSearchForm()
#             user_patients_search_form.region_id.choices = get_regions_choices(current_user)

#             patients_table = UserPatientsTableModule(request, Patient.query.filter_by(created_by_id=user.id),
#                                                     user_patients_search_form)

#             return route_template('users/add_user_and_profile', form = form, change=change, user=user,
#                                     patients_table=patients_table, error_msg=error_msg, is_profile=True)
#     else:    
#         return render_template('errors/error-500.html'), 500

# @blueprint.route('/delete_user', methods=['POST'])
# @login_required
# def delete_user():
#     if not current_user.is_authenticated:
#         return redirect(url_for('login_blueprint.login'))

#     if not current_user.is_admin:
#         return render_template('errors/error-500.html'), 500        
    
#     if len(request.form):
#         if "delete" in request.form:
#             user_id = request.form["delete"]
#             user = None
#             try:
#                 user = User.query.filter(User.id == user_id).first()
#             except exc.SQLAlchemyError:
#                 pass

#             if user:
#                 if Patient.query.filter_by(created_by_id=user.id).count():
#                     error_msg = _("Пользователь добавил пациентов. Удалите пациентов, добавленных пользователем")
#                     return redirect("{}?error={}".format(url_for('main_blueprint.users'), error_msg))

#                 db.session.delete(user)
#                 db.session.commit()

#     return redirect("{}?delete_user".format(url_for('main_blueprint.users')))