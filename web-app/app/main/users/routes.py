# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app.main import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager, db

from app.main.models import Region
from app.main.patients.models import Patient
from app.main.users.forms import CreateUserForm, UpdateUserForm
from app.main.forms import TableSearchForm
import math
from app.login.models import User
from app.main.util import get_regions, get_regions_choices, populate_form, disable_form_fields
from app.login.util import hash_pass
from flask_babelex import _
from app.main.routes import route_template
from jinja2 import TemplateNotFound
from app import constants as c
from sqlalchemy import exc

@blueprint.route('/users', methods=['GET'])
@login_required
def users():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500

    form = TableSearchForm()
    regions = get_regions(current_user)

    if not form.region.choices:
        form.region.choices = [ (-1, c.all_regions) ] + [(r.id, r.name) for r in regions]

    users = []
    filt = dict()

    q = User.query

    page = 1
    per_page = 5
    if "page" in request.args:
        page = int(request.args["page"])

    total_len = q.count()

    users = q.offset((page-1)*per_page).limit(per_page).all()

    for user in users:
        user.num_patients = Patient.query.filter_by(created_by = user).count()

    max_page = math.ceil(total_len/per_page)

    change = None
    error_msg = None

    if "added_user" in request.args:
        change =_("Пользователь был успешно добавлен")
    elif "delete_user" in request.args:
        change =_("Пользователь был успешно удален")
    elif "error" in request.args:
        error_msg = request.args["error"]

    form.process()
    return route_template('users/users', users=users, form=form, page=page, max_page=max_page, 
                                        total = total_len, constants=c, change=change, error_msg=error_msg)

@blueprint.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
        return render_template('errors/error-500.html'), 500

    form = CreateUserForm()

    if not form.region_id.choices:
        form.region_id.choices = get_regions_choices(current_user)

    form.process()

    if 'create' in request.form:
        new_dict = request.form.to_dict(flat=True)
        
        user = User.query.filter_by(username=new_dict['username'][0]).first()
        if user:
            return route_template( 'users/add_user', error_msg=_('Имя пользователя уже зарегистрировано'), form=form, change=None)

        if "is_admin" in new_dict:
            new_dict["is_admin"] = int(new_dict["is_admin"]) == 1

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

    if "id" in request.args:
        if request.args["id"] != str(current_user.id):
            if not current_user.is_admin:
                return render_template('errors/error-500.html'), 500

        user_query = User.query.filter_by(id=request.args["id"])
        user = user_query.first()

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
  
            form.process()

            return route_template('users/add_user_and_profile', form = form, change=change, user=user, error_msg=error_msg, is_profile=True)
    else:    
        return render_template('errors/error-500.html'), 500

@blueprint.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_authenticated:
        return redirect(url_for('login_blueprint.login'))

    if not current_user.is_admin:
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