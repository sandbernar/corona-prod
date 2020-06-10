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
from app.main.downloads.models import Download
from app.main.downloads.forms import DownloadSearchForm

import math
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields, parse_date
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc, func
from sqlalchemy.sql import select
import urllib
from datetime import datetime, timedelta

from app.main.downloads.modules import DownloadsTableModule

@blueprint.route('/downloads', methods=['GET'])
@login_required
def downloads():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_users and not current_user.user_role.can_export_users:
        return render_template('errors/error-500.html'), 500

    change = None
    error_msg = None

    if "added_user" in request.args:
        change =_("Пользователь был успешно добавлен")
    elif "delete_user" in request.args:
        change =_("Пользователь был успешно удален")
    elif "error" in request.args:
        error_msg = request.args["error"]

    downloads_search_form = DownloadSearchForm()

    q = Download.query

    # if not users_search_form.region_id.choices:
        # users_search_form.region_id.choices = [(-2, _("Неважно"))]
        # users_search_form.region_id.choices += get_regions_choices(current_user)

    # q_patient = db.session.query(Patient.created_by_id,
    #                                 func.count('*').label('patient_count'))    
    
    # q_patient = q_patient.group_by(Patient.created_by_id).subquery()
    # q = db.session.query(User, q_patient.c.patient_count).outerjoin(q_patient, User.id == q_patient.c.created_by_id)

    # header_buttons = []
    
    # if current_user.user_role.can_access_roles:
    #     header_buttons.append((_("Управление Ролями"), "users/roles"))

    # if current_user.user_role.can_add_edit_user:
    #     header_buttons.append((_("Добавить Пользователя"), "add_user"))
    
    downloads_table = DownloadsTableModule(request, q, downloads_search_form)

    # user_allowed_exports = False
    
    if current_user.user_role.can_export_patients or \
        current_user.user_role.can_export_contacted or \
        current_user.user_role.can_export_contacted or \
        current_user.user_role.can_export_users or \
        current_user.user_role.can_access_various_exports:
            user_allowed_exports = True

    downloads_search_form.process()
    # form.process()
    return route_template('downloads/downloads', downloads_table=downloads_table,  user_allowed_exports=user_allowed_exports,
                            downloads_search_form=downloads_search_form, constants=c, change=change, error_msg=error_msg)