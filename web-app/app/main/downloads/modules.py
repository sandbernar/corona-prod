from flask import request
import math
from app.main.modules import TableModule

from app import celery

import app.constants as c
from app.login.models import User
from app.main.patients.models import Patient

from collections import OrderedDict
from app.main.util import parse_date
from sqlalchemy import func
from flask_babelex import _

class DownloadsTableModule(TableModule):
    def __init__(self, request, q, search_form, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("Название")] = ["download_name"]
        table_head[_("Дата")] = ["created_date"]
        table_head[_("Прогресс")] = []

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
        # username = result[0].username
        # username = (username, "/user_profile?id={}".format(result[0].id))

        # email = result[0].email
        # region = c.all_regions if result[0].region == None else result[0].region

        # is_admin = _("Нет")
        # if result[0].is_admin:
        #     is_admin = _("Да")
        
        # telephone = result[0].telephone
        # added_patients_count = 0 if result[1] == None else result[1]

        # return [username, email, region, is_admin, telephone, added_patients_count]
        download_name = result.download_name
        created_date = result.created_date
        progress = celery.AsyncResult(result.task_id).state

        return [download_name, created_date, progress]
