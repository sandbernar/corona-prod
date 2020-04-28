from flask import request
import math
from app.main.modules import TableModule

import app.constants as c
from app.login.models import User

from collections import OrderedDict
from app.main.util import parse_date
from sqlalchemy import func
from flask_babelex import _

class UserTableModule(TableModule):
    def __init__(self, request, q, search_form, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("Логин")] = ["username"]
        table_head[_("E-Mail")] = ["email"]
        table_head[_("Регион")] = []
        table_head[_("Администратор?")] = ["is_admin"]
        table_head[_("Телефон")] = ["telephone"]
        table_head[_("Добавлено Пациентов")] = []

        super().__init__(request, q, table_head, header_button, search_form)     

    def search_table(self):
        username_value = self.request.args.get("username", None)
        if username_value:
            self.q = self.q.filter(func.lower(User.username).contains(username_value.lower()))
            
            self.search_form.username.default = username_value

        region_id = self.request.args.get("region_id", None)
        if region_id:
            try:
                region_id = int(region_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if region_id != -2:
                query_region_id = region_id
                if region_id == -1:
                    query_region_id = None

                self.q = self.q.filter(User.region_id == query_region_id)
                self.search_form.region_id.default = region_id

        is_admin = self.request.args.get("is_admin", "-1")
        if is_admin != "-1":
            try:
                self.q = self.q.filter(User.is_admin == bool(int(is_admin)))
            except ValueError:
                return render_template('errors/error-500.html'), 500                
            
            self.search_form.is_admin.default = is_admin        

    def print_entry(self, result):
        username = result[0].username
        username = (username, "/user_profile?id={}".format(result[0].id))

        email = result[0].email
        region = c.all_regions if result[0].region == None else result[0].region

        is_admin = _("Нет")
        if result[0].is_admin:
            is_admin = _("Да")
        
        telephone = result[0].telephone

        return [username, email, region, is_admin, telephone, result[1]]

class UserPatientsTableModule(TableModule):
    def __init__(self, request, q, search_form, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("ФИО")] = ["second_name", "first_name", "patronymic_name"]
        table_head[_("ИИН")] = ["iin"]
        table_head[_("Телефон")] = ["telephone"]
        table_head[_("Регион")] = []
        table_head[_("Время Добавления")] = ["created_date"]
        
        super().__init__(request, q, table_head, header_button, search_form, 
                        table_title=_("Пациенты, добавленные пользователем"))     

    def search_table(self):
        full_name_value = self.request.args.get("full_name", None)
        if full_name_value:
            self.q = self.q.filter(func.lower(func.concat(Patient.first_name, ' ', Patient.second_name, ' ', 
                                    Patient.patronymic_name)).contains(full_name_value.lower()))
            
            self.search_form.full_name.default = full_name_value

        region_id = self.request.args.get("region", -1)
        if region_id:
            try:
                region_id = int(region_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if region_id != -1:
                self.q = self.q.filter(Patient.region_id == region_id)
                self.search_form.region.default = region_id

        iin = self.request.args.get("iin", None)
        if iin:
            self.q = self.q.filter(Patient.iin.contains(iin))
            form.iin.default = iin
  

    def print_entry(self, result):
        full_name = (result, "/patient_profile?id={}".format(result.id))
        iin = result.iin
        telephone = result.telephone
        region = result.region
        created_date = result.created_date.strftime("%d-%m-%Y %H:%M")

        return [full_name, iin, telephone, region, created_date]