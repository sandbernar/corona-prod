# -*- encoding: utf-8 -*-
"""
License: MIT
"""

from flask_wtf import FlaskForm
from wtforms import TextField, SelectField, RadioField, DateField, BooleanField
from wtforms.validators import DataRequired
from flask_babelex import _

class CreateUserForm(FlaskForm):
    full_name = TextField('Full Name', validators=[DataRequired()])

    username = TextField('Username', validators=[DataRequired()])
    password = TextField('Password', validators=[DataRequired()])

    email    = TextField('Email')
    telephone    = TextField('Telephone')

    region_id = SelectField('Region', validators=[DataRequired()])
    organization = TextField('Organization', validators=[DataRequired()])
    user_role_id = SelectField('Region', validators=[DataRequired()])
    # is_admin = RadioField("Is Admin", choices=[(1, _("Да")), (0, _("Нет"))], default=0, validators=[DataRequired()])

class UpdateUserForm(CreateUserForm):
    password = TextField('Password', validators=[])

class UserSearchForm(FlaskForm):
    username = TextField('Username')
    region_id = SelectField('Region')
    user_role_id = SelectField('Region', validators=[DataRequired()])
    # is_admin = SelectField("Is Admin", choices=[(-1, _("Неважно")), (1, _("Да")), (0, _("Нет"))], default=-1)

class UserActivityReportForm(FlaskForm):
    region_id = SelectField('Region')
    start_date = DateField('Report Start Date')
    end_date = DateField('Report End Date')

class UserPatientsSearchForm(FlaskForm):
    full_name = TextField("Full Name")
    region_id = SelectField("Region ID")
    iin = TextField("IIN")    

class CreateUserRoleForm(FlaskForm):
    name = TextField("Role Name", validators=[DataRequired()])
    value = TextField("Role Value", validators=[DataRequired()])
    
    # Travel Types
    can_add_air = BooleanField()
    can_add_train = BooleanField()
    can_add_auto = BooleanField()
    can_add_foot = BooleanField()
    can_add_sea = BooleanField()
    can_add_local = BooleanField()
    can_add_blockpost = BooleanField()
    can_see_success_add_window = BooleanField()

    # Patient Profile Access
    can_lookup_own_patients = BooleanField()
    can_lookup_other_patients = BooleanField()
    can_access_contacted = BooleanField()
    can_delete_own_patients = BooleanField()
    can_delete_other_patients = BooleanField()
    can_lookup_other_regions_stats = BooleanField()

    # Profile Edit
    can_found_by_default = BooleanField()
    can_set_infected = BooleanField()
    can_set_hospital_home_quarant = BooleanField()
    can_set_transit = BooleanField()

    # Manager's Functions
    can_export_patients = BooleanField()
    can_export_contacted = BooleanField()
    can_access_various_exports = BooleanField()
    can_add_edit_hospital = BooleanField()

    # Admin Function
    can_block_own_region_accounts = BooleanField()
    can_block_all_accounts = BooleanField()
    can_access_roles = BooleanField()
    can_access_users = BooleanField()
    can_export_users = BooleanField()
    can_add_edit_user = BooleanField()
    can_access_user_info = BooleanField()