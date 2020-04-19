from flask import request
import math
from app.main.modules import TableModule
from app.main.flights_trains.models import TrainTravel, Train, FlightCode, FlightTravel
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