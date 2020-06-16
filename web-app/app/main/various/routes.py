# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2020 - Artem Fedoskin
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request, Response
from flask_login import login_required, current_user
from app import login_manager, db, celery

import pandas as pd
import io

from app.main.models import Region
from app.main.hospitals.models import Hospital_Type, Hospital
from app.main.patients.models import Patient, PatientState, State, ContactedPersons
from app.main.various.forms import DownloadVariousData
from app.main.forms import TableSearchForm
import math
from app.login.models import User
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields, parse_date, yes_no
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc, extract, func, cast, JSON, String, or_, text
from sqlalchemy.sql import select
import urllib
from datetime import datetime, timedelta, date

from app.main.celery_util import start_task, finish_task

from app.main.users.modules import UserTableModule, UserPatientsTableModule

def get_gen_stat(request, q, type_="all"):
    infected_state_id = State.query.filter_by(value=c.state_infec[0]).first().id
    hospitalized_state_id = State.query.filter_by(value=c.state_hosp[0]).first().id

    data = []

    date = request.form.get("date", datetime.today())
    if not date:
        date = datetime.today()
    else:
        date = parse_date(date)

    date = date.date()
    prev_date = date - timedelta(days=1)

    if type_ == "wo_symptoms":
        q = q.filter(cast(PatientState.attrs["state_infec_illness_symptoms"], db.String) == "'{}'".format(c.without_symptoms))
    elif type_ == "w_symptoms":
        q = q.filter(cast(PatientState.attrs["state_infec_illness_symptoms"], db.String) == "'{}'".format(c.with_symptoms))

    for region in Region.query.all():
        if region.name != "Вне РК":
            region_q = q.filter(Patient.region_id == region.id)
            region_q_date = region_q.filter(PatientState.detection_date == date)
            region_q_prev_date = region_q.filter(PatientState.detection_date == prev_date)
            
            def count_increase(a, b):
                increase = 0
                if b != 0:
                    increase = round(((a - b)/b)*100, 2)

                return increase

            infected_count = region_q_date.count()
            prev_day_infected_count = region_q_prev_date.count()
            
            infec_increase_percent = count_increase(infected_count, prev_day_infected_count)

            def symptoms_count(params):
                params_q = []

                for p in params:
                    params_q.append(text("CAST(\"PatientState\".attrs ->> '{}' AS VARCHAR) = '{}'".format(p[0], p[1])))

                symptoms_q = region_q_date.filter(or_(*params_q))
                symptoms = symptoms_q.count()

                symptoms_prev_day = region_q_prev_date.filter(or_(*params_q)).count()
                symptoms_increase = count_increase(symptoms, symptoms_prev_day)

                return symptoms, symptoms_increase

            wo_symptoms, wo_symptoms_increase = symptoms_count([("state_infec_illness_symptoms", c.without_symptoms[0])])
            w_symptoms, w_symptoms_increase = symptoms_count([("state_infec_illness_symptoms", c.with_symptoms[0])])

            prof_screen, prof_screen_increase = symptoms_count([("state_infec_type", c.prof_tzel[0]), ("state_infec_type", c.contacted_prof_tzel[0])])
            self_request, self_request_increase = symptoms_count([("state_infec_type", c.self_request[0]), ("state_infec_type", c.contacted_self_request[0])])

            zavoznoi, zavoznoi_increase = symptoms_count([("state_infec_type", c.zavoznoi[0]), ("state_infec_type", c.contacted_zavoznoi[0])])
            contacted, contacted_increase = symptoms_count([("state_infec_type", c.contacted_self_request[0]),
                                                            ("state_infec_type", c.contacted_prof_tzel[0]),
                                                            ("state_infec_type", c.contacted_zavoznoi[0])])

            unknown, unknown_increase = symptoms_count([("state_infec_type", -1)])

            overall_count = Patient.query.join(PatientState, PatientState.patient_id == Patient.id)
            overall_count = overall_count.filter(Patient.region_id == region.id)
            overall_count = overall_count.filter(PatientState.state_id == infected_state_id).group_by(Patient.id).count()

            contact_q = ContactedPersons.query.join(Patient, ContactedPersons.contacted_patient_id == Patient.id)
            contact_q = contact_q.filter(Patient.region_id == region.id)

            date_contact = contact_q.filter(Patient.created_date == date)
            prev_date_contact = contact_q.filter(Patient.created_date == prev_date)

            close_date_contact = date_contact.filter(ContactedPersons.is_potential_contact == False).count()
            close_prev_date_contact = date_contact.filter(ContactedPersons.is_potential_contact == False).count()
            close_contact_increase = count_increase(close_date_contact, close_prev_date_contact)

            potential_date_contact = date_contact.filter(ContactedPersons.is_potential_contact == True).count()
            potential_prev_date_contact = date_contact.filter(ContactedPersons.is_potential_contact == True).count()
            potential_contact_increase = count_increase(close_date_contact, close_prev_date_contact)

            hospitalized_count = Patient.query.join(PatientState, PatientState.patient_id == Patient.id)
            hospitalized_count = hospitalized_count.filter(Patient.region_id == region.id)
            hospitalized_count = hospitalized_count.filter(PatientState.detection_date == date)
            hospitalized_count = hospitalized_count.filter(PatientState.state_id == hospitalized_state_id).group_by(Patient.id).count()

            entry = [region.name, infected_count, infec_increase_percent,
                        close_date_contact, potential_date_contact]

            if type_ == "all":
                entry += [wo_symptoms, wo_symptoms_increase, w_symptoms, w_symptoms_increase]

            entry += [prof_screen, prof_screen_increase, self_request, self_request_increase,
                        zavoznoi, zavoznoi_increase, contacted, contacted_increase,
                        unknown, unknown_increase,
                        overall_count,
                        close_contact_increase, potential_contact_increase,
                        hospitalized_count]

            data.append(entry)

    infec_day_header = "{} {}".format(_("инфицировано за \n"), date.strftime("%d-%m-%Y"))

    columns = [_("Регион"), infec_day_header, _("прирост (%)"), _("установлено БК"), _("установлено ПК")]
    
    if type_ == "all":
        columns += [_("без \n симптомов"), _("%"), _("с \n симптомами"), _("%")]
    
    columns += [_("профскрининг"), _("%"), _("самообращение"), _("%"),
                _("завозной"), _("%"), _("контактных"), _("%"),
                _("статус \n не известен"), _("%"),
                _("всего зарегистрировано \n инфицированных с 13 марта"),
                _("БК в нарастании"), _("ПК в нарастании"),
                _("изолировано в карантинный \n стационар")]

    data = pd.DataFrame(data, columns=columns)

    return data
# =======
# @celery.task(bind=True)
# def export_region_age_sex_infected(self, filename):
#     def get_age_filter(age_start, age_end):
#         date_start = datetime.strftime(datetime.today() - timedelta(days=age_start*365), "%Y-%m-%d")
#         date_end = datetime.strftime(datetime.today() - timedelta(days=age_end*365), "%Y-%m-%d")

#         return Patient.dob.between(date_end, date_start)

#     q = Patient.query
    
#     infected_state_id = State.query.filter_by(value=c.state_infec[0]).first().id

#     q = q.join(PatientState, PatientState.patient_id == Patient.id)
#     q = q.filter(PatientState.state_id == infected_state_id)
#     q = q.group_by(Patient.id)

#     total = Region.query.count()
#     i = 0

#     data = []

#     for region in Region.query.all():
#         if region.name != "Вне РК":
#             infected_count = q.filter(Patient.region_id == region.id).count()

#             entry = [region.name, infected_count]
            
#             for age_range in [(0, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69)
#                               , (70, 79), (80, 89), (90, 99)]:
                
#                 age_query = q.filter(get_age_filter(age_range[0], age_range[1])).filter(Patient.region_id == region.id)     
                
#                 entry.append(age_query.filter(Patient.gender == False).count())
#                 entry.append(age_query.filter(Patient.gender == True).count())

#             data.append(entry)

#         self.update_state(state='PROGRESS',
#                             meta={'current': i, 'total': total,
#                             'status': 'PROGRESS'})
#         i += 1

#     age_ranges = [ _("0-9"), _("10-19"), _("20-29"), _("30-39"), _("40-49"), _("50-59"), _("60-69"),
#                    _("70-79"), _("80-89"), _("90-99")]

#     gender_age_ranges = [["М {}".format(age_r), "Ж {}".format(age_r)] for age_r in age_ranges]
#     gender_age_ranges = [x for l in gender_age_ranges for x in l]

#     data = pd.DataFrame(data, columns=[_("Регион"), _("Все"), *gender_age_ranges])

#     finish_task(data, self.request.id, filename)
# >>>>>>> 5453bc5a69c8962e946f34b252fbcfd6008e5e39

@blueprint.route('/export_various_data_xls', methods=['POST'])
@login_required
def export_various_data_xls():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_various_exports:
        return render_template('errors/error-500.html'), 500

    q = Patient.query
    
    infected_state_id = State.query.filter_by(value=c.state_infec[0]).first().id
    hospitalized_state_id = State.query.filter_by(value=c.state_hosp[0]).first().id

    q = q.join(PatientState, PatientState.patient_id == Patient.id)
    q = q.filter(PatientState.state_id == infected_state_id)
    q = q.group_by(Patient.id)

    data = []

    value = request.form.get("value", None)

    if value == "region_age_sex_infected":
        # task = export_region_age_sex_infected.delay(filename = "sss.xls")
        # start_task(current_user, _("Инфицированные - регион, возраст, пол"), task.id)
        # def export_region_age_sex_infected(self, filename):
        def get_age_filter(age_start, age_end):
            date_start = datetime.strftime(datetime.today() - timedelta(days=age_start*365), "%Y-%m-%d")
            date_end = datetime.strftime(datetime.today() - timedelta(days=age_end*365), "%Y-%m-%d")

            return Patient.dob.between(date_end, date_start)

        q = Patient.query
        
        infected_state_id = State.query.filter_by(value=c.state_infec[0]).first().id

        q = q.join(PatientState, PatientState.patient_id == Patient.id)
        q = q.filter(PatientState.state_id == infected_state_id)
        q = q.group_by(Patient.id)

        total = Region.query.count()
        i = 0

        data = []

        for region in Region.query.all():
            if region.name != "Вне РК":
                infected_count = q.filter(Patient.region_id == region.id).count()

                entry = [region.name, infected_count]
                
                for age_range in [(0, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69)
                                  , (70, 79), (80, 89), (90, 99)]:
                    
                    age_query = q.filter(get_age_filter(age_range[0], age_range[1])).filter(Patient.region_id == region.id)     
                    
                    entry.append(age_query.filter(Patient.gender == False).count())
                    entry.append(age_query.filter(Patient.gender == True).count())

                data.append(entry)

            # self.update_state(state='PROGRESS',
            #                     meta={'current': i, 'total': total,
            #                     'status': 'PROGRESS'})
            i += 1

        age_ranges = [ _("0-9"), _("10-19"), _("20-29"), _("30-39"), _("40-49"), _("50-59"), _("60-69"),
                       _("70-79"), _("80-89"), _("90-99")]

        gender_age_ranges = [["М {}".format(age_r), "Ж {}".format(age_r)] for age_r in age_ranges]
        gender_age_ranges = [x for l in gender_age_ranges for x in l]

        data = pd.DataFrame(data, columns=[_("Регион"), _("Все"), *gender_age_ranges])
    
    elif value == "region_geo_age":
        def calculate_age(born):
            today = date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        count = 0

        start_count = request.form.get("start_count", "")
        end_count = request.form.get("end_count", "")

        for patient in q.all():
            entry = []
            hospital_state_id = State.query.filter_by(value=c.state_hosp[0]).first().id

            if patient.region and patient.region.name != "Вне РК" and patient.home_address:
                count += 1
                if start_count != "" and end_count != "":
                    if count < int(start_count):
                        continue
                    if count > int(end_count):
                        break

                were_hospitalized = PatientState.query.filter_by(patient_id = patient.id).filter_by(state_id = hospital_state_id).count()

                gender = _("Неизвестно")

                if patient.gender == False:
                    gender = _("Мужчина")
                elif patient.gender == True:
                    gender = _("Женщина")

                contacted_count = ContactedPersons.query.filter_by(infected_patient_id=patient.id).count()
                is_contacted = ContactedPersons.query.filter_by(contacted_patient_id=patient.id).count()

                entry = [patient.region, patient.home_address.lat, patient.home_address.lng,
                        patient.home_address.city, patient.home_address.street, 
                        patient.dob, gender, patient.travel_type, yes_no(were_hospitalized),
                        contacted_count, yes_no(is_contacted),
                        yes_no(patient.is_dead), patient.job, patient.job_address,
                        patient.job_address.lat, patient.job_address.lng]
                
                if start_count != "" and end_count != "":
                    if count >= int(start_count) and count <= int(end_count):
                        data.append(entry)
                else:
                    data.append(entry)

        data = pd.DataFrame(data, columns=[_("Регион"), _("Latitude"), _("Longitude"),
                                           _("Город"), _("Улица"), _("Дата Рождения"), _("Пол"),
                                           _("Тип Въезда"), _("Был ли Госпитализирован"),
                                           _("Число Контактов"), _("Контактный?"),
                                           _("Умер"), _("Место Работы"), _("Адрес Работы"),
                                           _("Работа Lat"), _("Работа Lng")])

    elif value == "hospitals_list_by_regions":
        hospitals_q = Hospital.query

        hospital_type = request.form.get("hospital_type", "-1")
        if hospital_type != "-1":
            hospitals_q = hospitals_q.filter_by(hospital_type_id = hospital_type)

        for hospital in hospitals_q.all():
            entry = [str(hospital.region), hospital.hospital_type, str(hospital)]

            data.append(entry)

        data = pd.DataFrame(data, columns=[_("Регион"), _("Тип Стационара"), _("Название Стационара")])

    elif value == "infected_with_params":
        start_date = request.form.get("start_date", None)
        if start_date:
            start_date = parse_date(start_date)
            q = q.filter(PatientState.detection_date >= start_date)

        end_date = request.form.get("end_date", None)
        if end_date:
            end_date = parse_date(end_date)
            q = q.filter(PatientState.detection_date <= end_date)

        for patient in q.all():
            infected_state = PatientState.query.filter_by(patient_id = patient.id).filter_by(state_id = infected_state_id).first()

            if infected_state:

                state_infec_attr = c.unknown[1]
                illness_symptoms = c.unknown[1]
                illness_severity = c.unknown[1]

                if infected_state.attrs:
                    state_infec_attr = infected_state.attrs.get('state_infec_type', None)
                    if state_infec_attr:
                        state_infec_attr = dict(c.state_infec_types).get(state_infec_attr, c.unknown[1])

                    illness_symptoms = infected_state.attrs.get('state_infec_illness_symptoms', None)
                    if illness_symptoms != c.unknown[1] and illness_symptoms:
                        illness_symptoms = dict(c.illness_symptoms).get(illness_symptoms, c.unknown[1])

                    illness_severity = infected_state.attrs.get('state_infec_illness_severity', None)
                    if illness_severity != c.unknown[1] and illness_severity:
                        illness_severity = dict(c.illness_severity).get(illness_severity, c.unknown[1])

                entry = [str(patient), patient.dob, str(patient.home_address),
                        patient.job, patient.job_position, patient.job_category,
                        state_infec_attr, illness_symptoms, illness_severity]

                data.append(entry)

        data = pd.DataFrame(data, columns=[_("ФИО"), _("Год рождения"), _("Адрес"),
                                           _("Место работы"), _("Профессия (должность)"), _("Категория Работы"),
                                           _("Как выявлен"),
                                           _("Клиника"), _("Степень Симптомов")])
    elif value == "gen_stat_1_day":
        data = get_gen_stat(request, q)
    elif value == "gen_stat_1_day_wo_symptoms":
        data = get_gen_stat(request, q, "wo_symptoms")
    elif value == "gen_stat_1_day_w_symptoms":
        data = get_gen_stat(request, q, "w_symptoms")

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    data.to_excel(writer, index=False)

    def get_col_widths(df):
        widths = []
        for col in df.columns:
            col_data_width = len(col)

            if col_data_width < 5:
                col_data_width = 5

            if not isinstance(df[col], pd.DataFrame):
                col_data_width = max(df[col].map(str).map(len).max(), len(col))

                if col_data_width < 40:
                    col_data_width *= 1.2

            widths.append(col_data_width)

        return widths

    for i, width in enumerate(get_col_widths(data)):
        writer.sheets['Sheet1'].set_column(i, i, width)

    writer.sheets['Sheet1'].set_row(0, 30)

    writer.save()
    xlsx_data = output.getvalue()

    filename_xls = "выгрузка.xls"
    
    response = Response(xlsx_data, mimetype="application/vnd.ms-excel")
    response.headers["Content-Disposition"] = \
        "attachment;" \
        "filename*=UTF-8''{}".format(urllib.parse.quote(filename_xls.encode('utf-8')))

    return response
    # return redirect(url_for('main_blueprint.downloads'))

@blueprint.route('/various', methods=['GET'])
@login_required
def various():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_various_exports:
        return render_template('errors/error-500.html'), 500

    form = DownloadVariousData()

    form.hospital_type.choices = [c.all_types] + [(t.id, t.name) for t in Hospital_Type.query.all()]

    change = None
    error_msg = None

    return route_template('various/various', form=form, change=change, error_msg=error_msg)