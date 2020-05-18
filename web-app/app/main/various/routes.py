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
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields, parse_date, yes_no
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc, extract, func
from sqlalchemy.sql import select
import urllib
from datetime import datetime, timedelta, date

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

    value = request.form.get("value", None)

    if value == "region_age_sex_infected":
        def get_age_filter(age_start, age_end):
            date_start = datetime.strftime(datetime.today() - timedelta(days=age_start*365), "%Y-%m-%d")
            date_end = datetime.strftime(datetime.today() - timedelta(days=age_end*365), "%Y-%m-%d")

            return Patient.dob.between(date_end, date_start)

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

                entry = [patient.region, patient.home_address.lat, patient.home_address.lng,
                        calculate_age(patient.dob), patient.travel_type, yes_no(were_hospitalized)]
                
                if start_count != "" and end_count != "":
                    if count >= int(start_count) and count <= int(end_count):
                        data.append(entry)
                else:
                    data.append(entry)

        data = pd.DataFrame(data, columns=[_("Регион"), _("Latitude"), _("Longitude"), _("Возраст"), _("Тип Въезда"), _("Был ли Госпитализирован")])        

    # output = io.BytesIO()
    # # writer = pd.ExcelWriter(output, engine='xlsxwriter')
    # data.to_excel(writer, index=False)
    # data.to_csv()

    # def get_col_widths(df):
    #     widths = []
    #     for col in df.columns:
    #         col_data_width = max(df[col].map(str).map(len).max(), len(col))
    #         col_data_width *= 1.2

    #         widths.append(col_data_width)
        
    #     return widths

    # for i, width in enumerate(get_col_widths(data)):
    #     writer.sheets['Sheet1'].set_column(i, i, width)

    # writer.save()
    # xlsx_data = output.getvalue()

    # region_name = Region.query.filter_by(id = region_id).first().name if region_id != -1 else c.all_regions
    filename_xls = "выгрузка.csv"
    
    response = Response(data.to_csv(), mimetype="text/csv")
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