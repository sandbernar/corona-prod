from flask import request
import math
from app.main.modules import TableModule

import app.constants as c
from app.login.models import User
from app.main.patients.models import Patient

from collections import OrderedDict
from app.main.util import parse_date
from sqlalchemy import func
from flask_babelex import _


class HospitalPatientsTableModule(TableModule):
    def __init__(self, request, q, search_form, hospital_id, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("ФИО")] = ["second_name"]
        table_head[_("ИИН")] = ["iin"]
        table_head[_("Телефон")] = ["telephone"]
        table_head[_("Регион")] = []
        table_head[_("Время Добавления")] = ["created_date"]

        q = q.filter_by(hospital_id = hospital_id)
        
        super().__init__(request, q, table_head, header_button, search_form, 
                        table_title=_("Пациенты, госпитализированные в данном стационаре"))     

    def search_table(self):
        full_name_value = self.request.args.get("full_name", None)
        if full_name_value:
            self.q = self.q.filter(func.lower(func.concat(Patient.second_name, ' ', Patient.first_name, ' ', 
                                    Patient.patronymic_name)).contains(full_name_value.lower()))
            
            self.search_form.full_name.default = full_name_value

        region_id = self.request.args.get("region_id", -1)
        if region_id:
            try:
                region_id = int(region_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if region_id != -1:
                self.q = self.q.filter(Patient.region_id == region_id)
                self.search_form.region_id.default = region_id

        iin = self.request.args.get("iin", None)
        if iin:
            self.q = self.q.filter(Patient.iin.contains(iin))
            self.search_form.iin.default = iin

        if self.search_form:
            self.search_form.process()
  
    def print_entry(self, result):
        full_name = (result, "/patient_profile?id={}".format(result.id))
        iin = result.iin
        telephone = result.telephone
        region = result.region
        created_date = result.created_date.strftime("%d-%m-%Y %H:%M")

        return [full_name, iin, telephone, region, created_date]