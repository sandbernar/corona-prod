from flask import request
import math
from app.main.modules import TableModule

from app.main.patients.models import Patient, ContactedPersons

from collections import OrderedDict
from app.main.util import parse_date
from sqlalchemy import func
from flask_babelex import _
from app import constants as c

class ContactedPatientsTableModule(TableModule):
    def __init__(self, request, q, search_form, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("ФИО")] = ["second_name"]
        table_head[_("Телефон")] = ["telephone"]
        table_head[_("Тип Въезда")] = ["travel_type_id"]
        table_head[_("Регион")] = []
        table_head[_("Найден")] = ["is_found"]
        table_head[_("Госпитализирован")] = []

        super().__init__(request, q, table_head, header_button, search_form)

    def search_table(self):
        full_name_value = self.request.args.get("full_name", None)
        if full_name_value:
            self.q = self.q.filter(func.lower(func.concat(Patient.first_name, ' ', Patient.second_name, ' ', 
                                    Patient.patronymic_name)).contains(full_name_value.lower()))
            
            self.search_form.full_name.default = full_name_value

        region_id = self.request.args.get("region_id", -1)
        if region_id:
            region_id = int(region_id)

            if region_id != -1:
                self.q = self.q.filter(Patient.region_id == region_id)
                self.search_form.region_id.default = region_id

        is_found = self.request.args.get("is_found", "-1")
        if is_found != "-1":
            self.q = self.q.filter(Patient.is_found == bool(int(is_found)))
            self.search_form.is_found.default = is_found                  

        self.search_form.process()

    def print_entry(self, result):
        result = result.contacted_patient

        patient_id = (result, "/patient_profile?id={}".format(result.id))
        telephone = result.telephone
        travel_type = result.travel_type
        region = result.region

        is_found = _("Нет")
        if result.is_found:
            is_found = _("Да")

        in_hospital = _("Нет")
        if result.status.value == c.in_hospital[0]:
            in_hospital = _("Да")

        return [patient_id, telephone, travel_type, region, is_found, in_hospital]