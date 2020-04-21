from flask import request
import math
from app.main.modules import TableModule

from app.main.flights_trains.models import TrainTravel, Train, FlightCode, FlightTravel
from app.main.patients.models import Patient

from collections import OrderedDict
from app.main.util import parse_date
from sqlalchemy import func
from flask_babelex import _

class TrainTableModule(TableModule):
    def __init__(self, request, search_form, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("Профиль Рейса")] = []
        table_head[_("Дата Отправления")] = ["departure_date"]
        table_head[_("Дата Прибытия")] = ["arrival_date"]
        table_head[_("Из")] = ["from_country", "from_city"]
        table_head[_("В")] = ["to_country", "to_city"]
        table_head[_("Кол-во Прибывших")] = []

        super().__init__(request, Train.query, table_head, header_button, search_form)

    def search_table(self):
        departure_date_value = self.request.args.get("departure_date", None)
        if departure_date_value:
            departure_date = parse_date(departure_date_value)
            
            self.q = self.q.filter(Train.departure_date >= departure_date)
            self.search_form.departure_date.default = departure_date

        arrival_date_value = self.request.args.get("arrival_date", None)
        if arrival_date_value:
            arrival_date = parse_date(arrival_date_value)
            
            self.q = self.q.filter(Train.arrival_date <= arrival_date)
            self.search_form.arrival_date.default = arrival_date

        from_country_id = self.request.args.get("from_country_id", -1)
        if from_country_id:
            try:
                from_country_id = int(from_country_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if from_country_id != -1:
                self.q = self.q.filter(Train.from_country_id == from_country_id)
                self.search_form.from_country_id.default = from_country_id

        to_country_id = self.request.args.get("to_country_id", -1)
        if to_country_id:
            try:
                to_country_id = int(to_country_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if to_country_id != -1:
                self.q = self.q.filter(Train.to_country_id == to_country_id)
                self.search_form.to_country_id.default = to_country_id

        from_city = self.request.args.get("from_city", None)
        if from_city:
            self.q = self.q.filter(func.lower(Train.from_city).contains(from_city.lower()))
            self.search_form.from_city.default = from_city

        to_city = self.request.args.get("to_city", None)
        if to_city:
            self.q = self.q.filter(func.lower(Train.to_city).contains(to_city.lower()))
            self.search_form.to_city.default = to_city

    def print_entry(self, result):
        profile = (_("Открыть Профиль"), "/train_profile?id={}".format(result.id))
        departure_date = result.departure_date
        arrival_date = result.arrival_date
        from_country = "{}, {}".format(result.from_country, result.from_city)
        to_country = "{}, {}".format(result.to_country, result.to_city)
        passengers_num = TrainTravel.query.filter_by(train_id=result.id).count()

        return [profile, departure_date, arrival_date, from_country, to_country, passengers_num]


class FlightTableModule(TableModule):
    def __init__(self, request, search_form, header_button = None, page = 1, per_page = 5):
        table_head = OrderedDict()
        table_head[_("Код Рейса")] = ["code"]
        table_head[_("Дата")] = ["date"]
        table_head[_("Из")] = ["from_country", "from_city"]
        table_head[_("В")] = ["to_country", "to_city"]
        table_head[_("Кол-во Прибывших")] = []

        super().__init__(request, FlightCode.query, table_head, header_button, search_form)

    def search_table(self):
        code_value = self.request.args.get("code", None)
        if code_value:
            self.q = self.q.filter(FlightCode.code.contains(code_value))
            self.search_form.code.default = code_value

        date_value = self.request.args.get("date", None)
        if date_value:
            date = parse_date(date_value)
            
            self.q = self.q.filter(FlightCode.date == date)
            self.search_form.date.default = date

        from_country_id = self.request.args.get("from_country_id", -1)
        if from_country_id:
            try:
                from_country_id = int(from_country_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if from_country_id != -1:
                self.q = self.q.filter(FlightCode.from_country_id == from_country_id)
                self.search_form.from_country_id.default = from_country_id

        to_country_id = self.request.args.get("to_country_id", -1)
        if to_country_id:
            try:
                to_country_id = int(to_country_id)
            except ValueError:
                return render_template('errors/error-500.html'), 500

            if to_country_id != -1:
                self.q = self.q.filter(FlightCode.to_country_id == to_country_id)
                self.search_form.to_country_id.default = to_country_id

        from_city = self.request.args.get("from_city", None)
        if from_city:
            self.q = self.q.filter(func.lower(FlightCode.from_city).contains(from_city.lower()))
            self.search_form.from_city.default = from_city

        to_city = self.request.args.get("to_city", None)
        if to_city:
            self.q = self.q.filter(func.lower(FlightCode.to_city).contains(to_city.lower()))
            self.search_form.to_city.default = to_city

    def print_entry(self, result):
        code = (result, "/flight_profile?id={}".format(result.id))
        date = result.date
        from_country = "{}, {}".format(result.from_country, result.from_city)
        to_country = "{}, {}".format(result.to_country, result.to_city)
        passengers_num = FlightTravel.query.filter_by(flight_code_id=result.id).count()

        return [code, date, from_country, to_country, passengers_num]

class PatientsTravelTableModule(TableModule):
    def __init__(self, request, q, search_form, is_trains = False, header_button = None, page = 1, per_page = 5):
        self.is_trains = is_trains

        table_head = OrderedDict()
        table_head[_("ФИО")] = ["second_name"]
        table_head[_("Телефон")] = ["telephone"]
        table_head[_("Регион")] = []
        table_head[_("Страна последние 14 дней")] = []
        
        if is_trains:
            table_head[_("Вагон")] = ["wagon"]

        table_head[_("Место")] = ["seat"]

        super().__init__(request, q, table_head, header_button, search_form)     

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

    def print_entry(self, result):
        full_name = (result[0], "/patient_profile?id={}".format(result[0].id))
        telephone = result[0].telephone
        region = result[0].region

        visited_country = _("Неизвестно")
        
        if result[0].visited_country != None:
            visited_country = ", ".join([ str(c) for c in result[0].visited_country])

        return_value = [full_name, telephone, region, visited_country]

        if self.is_trains:
            wagon = result[1].wagon
            return_value.append(wagon)

        return_value.append(result[1].seat)

        return return_value