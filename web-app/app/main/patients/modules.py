from flask import request
import math
from app.main.modules import TableModule

from app.main.patients.models import Patient, ContactedPersons

from collections import OrderedDict
from app.main.util import parse_date, yes_no_html
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
        table_head[_("Удалить Связь")] = []
        table_head[_("Добавлен в течение 2-х часов")] = []

        super().__init__(request, q, table_head, header_button, search_form, sort_param="contacted_patient")

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

        is_added_in_2_hours = self.request.args.get("is_added_in_2_hours", "-1")
        if is_added_in_2_hours != "-1":
            infected_patient_id = request.args['id']

            valid_ids = []
            for c in self.q.all():
                if c.added_in_n_hours() == bool(int(is_added_in_2_hours)):
                    valid_ids.append(c.id)

            self.q = self.q.filter(ContactedPersons.id.in_(valid_ids))


            # self.q = self.q.filter(Patient.is_found == bool(int(is_found)))
            self.search_form.is_added_in_2_hours.default = is_added_in_2_hours                            

        self.search_form.process()

    def print_entry(self, result):
        patient = result.contacted_patient

        patient_id = (patient, "/patient_profile?id={}".format(patient.id))
        telephone = patient.telephone
        travel_type = patient.travel_type
        region = patient.region

        is_found = yes_no_html(False)
        if patient.is_found:
            is_found = yes_no_html(True)

        in_hospital = yes_no_html(False)
        if patient.status and patient.status.value == c.in_hospital[0]:
            in_hospital = yes_no_html(True)

        delete_contact_html = "<a href=\"/delete_contacted?contact_id={}\" class=\"btn btn-danger\">{}</a>".format(
                                result.id, _("Удалить Связь"))
        delete_contact_button = (delete_contact_html, "safe")

        is_added_in_2_hours = yes_no_html(True if result.added_in_n_hours() else False)

        return [patient_id, telephone, travel_type, region, is_found, \
                in_hospital, delete_contact_button, is_added_in_2_hours]