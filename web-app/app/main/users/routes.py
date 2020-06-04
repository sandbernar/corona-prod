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
from app.main.patients.models import Patient
from app.main.users.forms import CreateUserForm, UpdateUserForm, UserActivityReportForm,\
                                    UserSearchForm, UserPatientsSearchForm, CreateUserRoleForm
from app.main.forms import TableSearchForm
import math
from app.login.models import User, UserRole
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

from app.main.users.modules import UserTableModule, UserPatientsTableModule, UserRolesTableModule

def setup_user_form(form):
    if not form.region_id.choices:
        form.region_id.choices = get_regions_choices(current_user)

    if not form.user_role_id.choices:
        roles = UserRole.query.all()
        form.user_role_id.choices = [(r.id, r.name) for r in roles]

@blueprint.route('/export_users_activity_xls', methods=['POST'])
@login_required
def export_users_activity_xls():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_export_users:
        return render_template('errors/error-500.html'), 500
   
    q_patient = db.session.query(Patient.created_by_id,
                                    func.count('*').label('patient_count'))

    start_date = request.form.get("start_date", None)
    if start_date:
        try:
            start_date = parse_date(start_date)
        except ValueError:
            return render_template('errors/error-500.html'), 500

        q_patient = q_patient.filter(Patient.created_date >= start_date)

    end_date = request.form.get("end_date", None)
    if end_date:
        try:
            end_date = parse_date(end_date)
        except ValueError:
            return render_template('errors/error-500.html'), 500

        # Add day so that we get data from throughout the whole day
        q_patient = q_patient.filter(Patient.created_date <= end_date + timedelta(days=1))

    q_patient = q_patient.group_by(Patient.created_by_id).subquery()
    q = db.session.query(User, q_patient.c.patient_count).outerjoin(q_patient, User.id == q_patient.c.created_by_id)

    region_id = request.form.get("region_id", None)
    if region_id:
        try:
            region_id = int(region_id)
        except ValueError:
            return render_template('errors/error-500.html'), 500

        if region_id != -1:
            q = q.filter(User.region_id == region_id)

    data = [[row[0].full_name, row[0].organization, row[0].region, row[1] if row[1] else 0] for row in q.all()]
    data = pd.DataFrame(data, columns=[_("ФИО"), _("Организация"), _("Регион"), _("Кол-во добавленных пациентов")])

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    data.to_excel(writer)
    writer.save()
    xlsx_data = output.getvalue()

    region_name = Region.query.filter_by(id = region_id).first().name if region_id != -1 else c.all_regions
    filename_xls = "{}_{}".format(_("пользователи"), region_name)

    if start_date:
        filename_xls = "{}_{}".format(filename_xls, start_date)

    if end_date:
        filename_xls = "{}_{}".format(filename_xls, end_date)

    filename_xls = "{}.xls".format(filename_xls)
    
    response = Response(xlsx_data, mimetype="application/vnd.ms-excel")
    response.headers["Content-Disposition"] = \
        "attachment;" \
        "filename*=UTF-8''{}".format(urllib.parse.quote(filename_xls.encode('utf-8')))

    return response

@blueprint.route('/users', methods=['GET'])
@login_required
def users():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_users and not current_user.user_role.can_export_users:
        return render_template('errors/error-500.html'), 500

    form = UserActivityReportForm()

    regions = get_regions(current_user)

    if not form.region_id.choices:
        form.region_id.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]
   
    change = None
    error_msg = None

    if "added_user" in request.args:
        change =_("Пользователь был успешно добавлен")
    elif "delete_user" in request.args:
        change =_("Пользователь был успешно удален")
    elif "error" in request.args:
        error_msg = request.args["error"]

    users_search_form = UserSearchForm()

    if not users_search_form.region_id.choices:
        users_search_form.region_id.choices = [(-2, _("Неважно"))]
        users_search_form.region_id.choices += get_regions_choices(current_user)

    q_patient = db.session.query(Patient.created_by_id,
                                    func.count('*').label('patient_count'))    
    
    q_patient = q_patient.group_by(Patient.created_by_id).subquery()
    q = db.session.query(User, q_patient.c.patient_count).outerjoin(q_patient, User.id == q_patient.c.created_by_id)

    header_buttons = []
    
    if current_user.user_role.can_access_roles:
        header_buttons.append((_("Управление Ролями"), "users/roles"))

    if current_user.user_role.can_add_edit_user:
        header_buttons.append((_("Добавить Пользователя"), "add_user"))
    
    users_table = UserTableModule(request, q, users_search_form, 
        header_button=header_buttons)

    users_search_form.process()
    form.process()
    return route_template('users/users', users=users, users_table = users_table, form=form,
                            users_search_form=users_search_form, constants=c, change=change, error_msg=error_msg)

@blueprint.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_add_edit_user:
        return render_template('errors/error-500.html'), 500

    form = CreateUserForm()
    setup_user_form(form)

    form.process()

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)
        
        user = User.query.filter_by(username=new_dict['username']).first()
        if user:
            return route_template( 'users/add_user_and_profile', error_msg=_('Имя пользователя уже зарегистрировано'), form=form, change=None)

        # if "is_admin" in new_dict:
            # new_dict["is_admin"] = int(new_dict["is_admin"]) == 1

        if 'region_id' in new_dict:
            if new_dict['region_id'] == '-1':
                new_dict['region_id'] = None

        user = User(**new_dict)
        
        db.session.add(user)
        db.session.commit()

        return redirect("{}?added_user".format(url_for('main_blueprint.users')))
    else:
        return route_template( 'users/add_user_and_profile', form=form, change=None, error_msg=None, is_profile=False)


@blueprint.route('/user_profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_add_edit_user:
        return render_template('errors/error-500.html'), 500       

    if "id" in request.args:
        if request.args["id"] != str(current_user.id):
            if not current_user.is_admin:
                return render_template('errors/error-500.html'), 500

        try:
            user_query = User.query.filter_by(id=request.args["id"])
            user = user_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400    
        
        if not user:
            return render_template('errors/error-404.html'), 404
        else:
            form = UpdateUserForm()
            
            change = None
            error_msg = None

            if not current_user.is_admin:
                form_fields = ["full_name", "username", "email", "region_id",
                                "telephone", "organization", "is_admin"]

                disable_form_fields(form, form_fields)
                                
            if 'update' in request.form:
                values = request.form.to_dict()

                if current_user.is_admin:
                    if 'username' in values:
                        new_username = values['username']
                        
                        if not new_username == user.username:
                            if not User.query.filter_by(username = new_username).count():
                                user.username = new_username
                            else:
                                error_msg = _("Пользователь с таким логином уже существует")

                    if 'region_id' in values:
                        if values['region_id'] == '-1':
                            values['region_id'] = None

                    if 'is_admin' in values:
                        values['is_admin'] = int(values['is_admin']) == 1
                else:
                    # Delete values that we don't update
                    values.pop("is_admin", None)
                    values.pop("username", None)
                    values.pop("region_id", None)

                if not error_msg:
                    if values.get('password', ''):
                        password = values['password']

                        user.password = hash_pass(password)

                    values.pop("password", None)
                    values.pop("csrf_token", None)
                    values.pop("update", None)
                    
                    user_query.update(values)

                    db.session.add(user)
                    db.session.commit()

                    change = _("Данные обновлены")
            
            user = user_query.first()
            user_parameters = user.__dict__.copy()

            user_parameters.pop("password", None)

            populate_form(form, user_parameters)
            form.region_id.choices = get_regions_choices(current_user)

            if not form.user_role_id.choices:
                roles = UserRole.query.all()
                form.user_role_id.choices = [(r.id, r.name) for r in roles]
  
            form.process()

            user_patients_search_form = UserPatientsSearchForm()
            user_patients_search_form.region_id.choices = get_regions_choices(current_user)

            patients_table = UserPatientsTableModule(request, Patient.query.filter_by(created_by_id=user.id),
                                                    user_patients_search_form)

            return route_template('users/add_user_and_profile', form = form, change=change, user=user,
                                    patients_table=patients_table, error_msg=error_msg, is_profile=True)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_add_edit_user:
        return render_template('errors/error-500.html'), 500         
    
    if len(request.form):
        if "delete" in request.form:
            user_id = request.form["delete"]
            user = None
            try:
                user = User.query.filter(User.id == user_id).first()
            except exc.SQLAlchemyError:
                pass

            if user:
                if Patient.query.filter_by(created_by_id=user.id).count():
                    error_msg = _("Пользователь добавил пациентов. Удалите пациентов, добавленных пользователем")
                    return redirect("{}?error={}".format(url_for('main_blueprint.users'), error_msg))

                db.session.delete(user)
                db.session.commit()

    return redirect("{}?delete_user".format(url_for('main_blueprint.users')))

@blueprint.route('/users/roles', methods=['GET'])
@login_required
def user_roles():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_roles:
        return render_template('errors/error-500.html'), 500 

    change = None
    error_msg = None

    if "added_role" in request.args:
        change =_("Роль была успешно добавлена")
    elif "delete_role" in request.args:
        change =_("Роль была успешно удалена")
    elif "error" in request.args:
        error_msg = request.args["error"]

    q = UserRole.query

    user_roles_table = UserRolesTableModule(request, q, header_button=[(_("Добавить Роль"), "/users/roles/add")])

    return route_template('users/user_roles', user_roles_table = user_roles_table, constants=c, change=change,
                            error_msg=error_msg)

@blueprint.route('/users/roles/role', methods=['GET', 'POST'])
def user_role_profile():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_roles:
        return render_template('errors/error-500.html'), 500

    if "id" in request.args:
        if request.args["id"] != str(current_user.id):
            if not current_user.user_role.can_access_roles:
                return render_template('errors/error-500.html'), 500
        try:
            role_query = UserRole.query.filter_by(id=request.args["id"])
            role = role_query.first()
        except exc.SQLAlchemyError:
            return render_template('errors/error-400.html'), 400    
        
        if not role:
            return render_template('errors/error-404.html'), 404
        else:
            form = CreateUserRoleForm()

            change = None
            error_msg = None
                                
            if 'update' in request.form:
                values = request.form.to_dict()

                values.pop('csrf_token')
                values.pop('update')

                for key in values.keys():
                    if values[key] == "y":
                        values[key] = True

                role_keys = list(role.__dict__.keys())
                role_keys.pop(role_keys.index('_sa_instance_state'))
                role_keys.pop(role_keys.index('id'))

                for key in role_keys:
                    if key not in values.keys():
                        values[key] = False
                    
                role_query.update(values)
                db.session.commit()

                change = _("Данные обновлены")           

            form.name.default = role.name
            form.value.default = role.value

            populate_form(form, role.__dict__.copy())

            form.process()

            return route_template('users/add_role_and_profile', form=form, change=change, error_msg=error_msg,
                                    role = role, is_profile=True)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/users/roles/add', methods=['GET', 'POST'])
def add_user_role():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.user_role.can_access_roles:
        return render_template('errors/error-500.html'), 500

    form = CreateUserRoleForm()

    form.process()

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)
        
        del new_dict["csrf_token"]
        del new_dict["create"]

        for key in new_dict.keys():
            if new_dict[key] == "y":
                new_dict[key] = True
        
        user_role = UserRole.query.filter_by(name=new_dict['name']).first()
        if user_role:
            return route_template( 'users/add_role_and_profile', error_msg=_('Роль с таким именем или кодом уже существует'), form=form, change=None)
        
        user = UserRole(**new_dict)
        
        db.session.add(user)
        db.session.commit()

        return redirect("{}?added_user_role".format(url_for('main_blueprint.users')))
    else:
        return route_template( 'users/add_role_and_profile', form=form, change=None, error_msg=None, is_profile=False)