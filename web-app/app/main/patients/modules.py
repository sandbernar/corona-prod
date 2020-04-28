from flask import request
import math
from app.main.modules import TableModule

from app.main.patients.models import Patient, ContactedPersons, PatientStatus
from app.main.models import TravelType, VariousTravel, BlockpostTravel
from app.main.flights_trains.models import FlightTravel, TrainTravel

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
            self.q = self.q.filter(func.lower(func.concat(Patient.second_name, ' ', Patient.first_name, ' ', 
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

class AllPatientsTableModule(TableModule):
    def __init__(self, request, q, select_contacted = None, search_form = None, header_button = None,\
                    page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("ФИО")] = ["first_name", "second_name", "patronymic_name"]
        table_head[_("ИИН")] = ["iin"]
        table_head[_("Тип Въезда")] = ["travel_type_id"]
        table_head[_("Регион")] = []
        table_head[_("Найден")] = ["is_found"]
        table_head[_("Госпитализирован")] = []
        table_head[_("Инфицирован")] = ["is_infected"]
        table_head[_("Контактов (найдено/всего)")] = []
        table_head[_("Время Добавления")] = ["created_date"]

        self.select_contacted = select_contacted

        if select_contacted:
            table_head[_("Выбрать контактных")] = []

            infected_contacted = ContactedPersons.query.filter_by(infected_patient_id=select_contacted)
            self.infected_contacted_ids = [c.contacted_patient_id for c in infected_contacted]

            contacted_infected = ContactedPersons.query.filter_by(contacted_patient_id=select_contacted)
            self.contacted_infected_ids = [c.infected_patient_id for c in contacted_infected]

        super().__init__(request, q, table_head, header_button, search_form)

    def search_table(self):
        full_name_value = self.request.args.get("full_name", None)
        if full_name_value:
            self.q = self.q.filter(func.lower(func.concat(Patient.second_name, ' ', Patient.first_name, ' ', 
                                    Patient.patronymic_name)).contains(full_name_value.lower()))
            
            self.search_form.full_name.default = full_name_value

        region_id = self.request.args.get("region_id", -1)
        if region_id:
            region_id = int(region_id)

            if region_id != -1:
                self.q = self.q.filter(Patient.region_id == region_id)
                self.search_form.region_id.default = region_id

        filt = dict()

        print(self.search_form.__dict__.keys())

        if "not_found" in request.args:
            filt["is_found"] = False
            self.search_form.not_found.default='checked'

        if "is_infected" in request.args:
            filt["is_infected"] = True
            self.search_form.is_infected.default='checked'

        if "not_in_hospital" in request.args:
            in_hospital_id = PatientStatus.query.filter_by(value=c.in_hospital[0]).first().id
            self.q = self.q.filter(Patient.status_id != in_hospital_id)

            self.search_form.not_in_hospital.default='checked'

        def name_search(param, param_str, q):
            if param_str in request.args:
                req_str = request.args[param_str]
                q = q.filter(func.lower(param).contains(req_str.lower()))
                param = getattr(self.search_form, param_str, None)
                if param:
                    setattr(param, 'default', req_str)
            
            return q

        self.q = name_search(Patient.first_name, "first_name", self.q)
        self.q = name_search(Patient.second_name, "second_name", self.q)
        self.q = name_search(Patient.patronymic_name, "patronymic_name", self.q)

        if "iin" in request.args:
            self.q = self.q.filter(Patient.iin.contains(request.args["iin"]))
            self.search_form.iin.default = request.args["iin"]

        if "telephone" in request.args:
            self.q = self.q.filter(Patient.telephone.contains(request.args["telephone"]))
            self.search_form.telephone.default = request.args["telephone"]

        travel_type = request.args.get("travel_type", c.all_travel_types[0])
        if travel_type and travel_type != c.all_travel_types[0]:
            try:
                travel_type_query = TravelType.query.filter_by(value=travel_type).first()
                travel_type_id = travel_type_query.id
            except exc.SQLAlchemyError:
                return render_template('errors/error-400.html'), 400

            if travel_type_id:
                filt["travel_type_id"] = travel_type_id
                self.search_form.travel_type.default = travel_type
        
        self.q = self.q.filter_by(**filt)

        if travel_type and travel_type != c.all_travel_types[0]:
            # FlightTravel
            if travel_type_query.value == c.flight_type[0]:
                self.q = self.q.join(FlightTravel)

                flight_code_id = request.args.get("flight_code_id", None)
                if flight_code_id != None:
                    self.q = self.q.filter(FlightTravel.flight_code_id == flight_code_id)
            
            # TrainTravel
            elif travel_type_query.value == c.train_type[0]:
                self.q = self.q.join(TrainTravel)

                train_id = request.args.get("train_id", None)
                if train_id != None:
                    self.q = self.q.filter(TrainTravel.train_id == train_id)

            # Blockpost
            elif travel_type_query.value == c.blockpost_type[0]:
                self.q = self.q.join(BlockpostTravel)

                arrival_date = request.args.get("arrival_date", None)
                if arrival_date:
                    self.q = self.q.filter(BlockpostTravel.date == arrival_date)
                    self.search_form.arrival_date.default = parse_date(arrival_date)

                blockpost_region_id = request.args.get("blockpost_region_id", "-1")
                if blockpost_region_id != "-1":
                    self.q = self.q.filter(BlockpostTravel.region_id == blockpost_region_id)
                    self.search_form.blockpost_region_id.default = blockpost_region_id

            # Auto
            elif (travel_type_query.value, travel_type_query.name) in c.various_travel_types:
                self.q = self.q.join(VariousTravel)

                arrival_date = request.args.get("arrival_date", None)
                if arrival_date:
                    self.q = self.q.filter(VariousTravel.date == arrival_date)
                    self.search_form.arrival_date.default = parse_date(arrival_date)
                
                border_id = request.args.get("auto_border_id", "-1")
                if border_id != "-1":
                    self.search_form.auto_border_id.default = border_id

                border_list = [("auto_border_id", self.search_form.auto_border_id),
                               ("foot_border_id", self.search_form.foot_border_id),
                               ("sea_border_id", self.search_form.sea_border_id)]
                
                for border_type in border_list:
                    if border_type[0] in request.args:
                        if request.args[border_type[0]] != "-1":
                            border_id = request.args[border_type[0]]
                            border_type[1].default = border_id
                
                            self.q = self.q.filter(VariousTravel.border_control_id == border_id)
                            break

        self.search_form.process()

    def print_entry(self, result):
        patient = result

        patient_id = (patient, "/patient_profile?id={}".format(patient.id))
        iin = patient.iin
        travel_type = patient.travel_type
        region = patient.region

        is_found = yes_no_html(False)
        if patient.is_found:
            is_found = yes_no_html(True)

        in_hospital = yes_no_html(False)
        if patient.status and patient.status.value == c.in_hospital[0]:
            in_hospital = yes_no_html(True)

        is_infected = yes_no_html(False, invert_colors=True)
        if patient.status and patient.is_infected:
            is_infected = yes_no_html(True, invert_colors=True)

        created_date = patient.created_date.strftime("%d-%m-%Y %H:%M")

        contacted = ContactedPersons.query.filter_by(infected_patient_id=patient.id).all()

        contacted_found_count = 0

        for contact in contacted:
            contacted_person = Patient.query.filter_by(id=contact.contacted_patient_id).first()
            if contacted_person and contacted_person.is_found:
                contacted_found_count += 1

        contacted_count = "{}/{}".format(contacted_found_count, len(contacted))

        row_to_print = [patient_id, iin, travel_type, region, is_found, \
                in_hospital, is_infected, contacted_count, created_date]

        if self.select_contacted:
            select_contacted_button = None

            if self.select_contacted == patient.id:
                select_contacted_button = _("Основной Пациент")
            elif patient.id in self.infected_contacted_ids:
                select_contacted_html = "<a href=\"/contacted_persons?id={}\" class=\"btn btn-success\">{}</a>".format(
                                        self.select_contacted, _("Контактный"))
                select_contacted_button = (select_contacted_html, "safe")                
            elif patient.id in self.contacted_infected_ids:
                select_contacted_html = "<a href=\"/contacted_persons?id={}\" class=\"btn btn-danger\">{}</a>".format(
                                        patient.id, _("Контактировал С"))
                select_contacted_button = (select_contacted_html, "safe")
            else:
                select_contacted_html = "<a href=\"/select_contacted?infected_patient_id={}&contacted_patient_id={}\" class=\"btn btn-primary\">{}</a>".format(
                                        self.select_contacted, patient.id, _("Выбрать Контактным"))
                select_contacted_button = (select_contacted_html, "safe")

            if select_contacted_button:
                row_to_print.append(select_contacted_button)

        return row_to_print