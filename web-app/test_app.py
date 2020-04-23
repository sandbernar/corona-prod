import os
import unittest
from config import config_dict
from flask_babelex import Babel

from flask import request, session
from time import sleep
from app import create_app, db
import random
import time

from app.login.util import hash_pass

from app.login.models import User

from app.main.patients.forms import PatientForm, UpdateProfileForm, AddFlightFromExcel

from flask_migrate import Migrate
from sqlalchemy import create_engine

from app.main.flights_trains.models import FlightCode, FlightTravel, Train, TrainTravel
from app.main.patients.models import Patient, PatientStatus, ContactedPersons, State, PatientState
import names

import string
from faker import Faker
def str_time_prop(start, end, format, prop):
    """Get a time at a proportion of a range of two formatted times.

    start and end should be strings specifying times formated in the
    given format (strftime-style), giving an interval [start, end].
    prop specifies how a proportion of the interval to be taken after
    start.  The returned time will be in the specified format.
    """

    stime = time.mktime(time.strptime(start, format))
    etime = time.mktime(time.strptime(end, format))

    ptime = stime + prop * (etime - stime)

    return time.strftime(format, time.localtime(ptime))


def random_date(start, end, prop):
    return str_time_prop(start, end, '%m-%d-%Y', prop)


class TestCase(unittest.TestCase):
    def setUp(self):
        get_config_mode = os.environ.get('CONFIG_MODE', 'Debug')
        config_mode = config_dict[get_config_mode.capitalize()]
        app = create_app(config_mode, unittest=True)
        app_ctx = app.app_context()
        app_ctx.push()
        babel = Babel(app)

        # Migrate(app, db)
        # engine = create_engine(config_mode.SQLALCHEMY_DATABASE_URI)

        # from sqlalchemy.orm import sessionmaker
        # Session = sessionmaker(bind = engine)
        # session = Session()
        # user = User()
        # user.username = "adm"
        # user.password = hash_pass("paswd")

        # user.full_name = "test1"
        # user.organization = "test2"
        # user.telephone = "s"
        # user.email = "s"
        # user.region_id = 1
        # db.session.add(user)
        # db.session.commit()

        self.app = app.test_client()
        # @babel.localeselector
        # def get_locale():
        #     if request.args.get('lang'):
        #         session['lang'] = request.args.get('lang')
        #     return session.get('lang', 'en')

    def tearDown(self):
        db.session.close()
        # db.drop_all()

    def test_base(self):
        response = self.app.get('/', content_type='html/text', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Login', str(response.data))

    def test_login(self):
        rv = self.login('adm', 'paswd')
        assert 'Dashboard' in str(rv.data)
        rv = self.logout()
        assert "Login" in str(rv.data)
        rv = self.login('adm', 'Wrong')
        assert 'Wrong' in str(rv.data)
        rv = self.login('admin', 'paswd')
        assert 'Wrong' in str(rv.data)

    def test_flight(self):
        self.login('adm', 'paswd')
        flight = {
            "code": "test",
            "date": random_date("1-1-2008", "1-1-2020", random.random()),
            "from_country_id": 88,
            "from_city": "Nur-Sultan",
            "to_country_id": 88,
            "to_city": "Astana",
            "create": "",
        }

        rv = self.app.post("/add_flight", data=flight, follow_redirects=True)
        assert "Рейс успешно добавлен" in str(rv.data.decode('utf-8'))

    def test_train(self):
        self.login('adm', 'paswd')
        train = {
            "departure_date": random_date("1-1-2008", "1-1-2020", random.random()),
            "arrival_date": random_date("1-1-2008", "1-1-2020", random.random()),
            "from_country_id": 88,
            "from_city": "Astana",
            "to_country_id": 88,
            "to_city": "Almaty",
            "create": ""
        }

        # POST /add_train HTTP/1.1
        rv = self.app.post("/add_train", data=train, follow_redirects=True)
        assert "Рейс успешно добавлен" in str(rv.data.decode('utf-8'))

    def test_new_patient(self):
        self.login("adm", "paswd")
        for i in range(1000):
            rv = self.add_patient()
            assert "patient_id" in str(rv.data)

    def test_new_patient_flight(self):
        self.login('adm', 'paswd')
        FLIGHT = FlightCode.query.all()[-1]
        patient = {
            "travel_type": "flight_type",
            "flight_arrival_date": FLIGHT.date,
            "flight_code_id": FLIGHT.id,
            "flight_seat": "1c",
            "second_name": "w",
            "first_name": "w",
            "patronymic_name": "",
            "gender": -1,
            "dob": "2020-04-17",
            "iin": "",
            "country_of_residence_id": 88,
            "citizenship_id": 88,
            "pass_num": "",
            "home_address_country_id": 88,
            "home_address_state": "",
            "home_address_county": "",
            "home_address_city": "w",
            "home_address_street": "",
            "home_address_house": "",
            "home_address_flat": "",
            "home_address_building": "",
            "visited_country_id": -1,
            "visited_from_date": "",
            "visited_to_date": "",
            "region_id": 1,
            "job": "",
            "job_position": "",
            "job_address_country_id": 88,
            "job_address_state": "",
            "job_address_county": "",
            "job_address_city": "",
            "job_address_street": "",
            "job_address_house": "",
            "job_address_flat": "",
            "job_address_building": "",
            "telephone": "",
            "email": "",
            "is_found": 0,
            "is_infected": 0,
            "is_contacted": 0,
            "create": ""
        }
        rv = self.app.post("/add_person", data=patient, follow_redirects=True)
        print(str(rv.data.decode('utf-8')))
        assert "patient_id" in str(rv.data)

    def test_new_patient_train(self):
        self.login("adm", "paswd")
        TRAIN = Train.query.all()[-1]
        patient = {
            "travel_type": "train_type",
            "train_departure_date": TRAIN.departure_date,
            "train_arrival_date": TRAIN.arrival_date,
            "train_id": TRAIN.id,
            "train_wagon": "32",
            "train_seat": "4",
            "second_name": "1",
            "first_name": "1",
            "patronymic_name": "",
            "gender": -1,
            "dob": "2020-04-10",
            "iin": "",
            "country_of_residence_id": 88,
            "citizenship_id": 88,
            "pass_num": "",
            "home_address_country_id": 88,
            "home_address_state": "",
            "home_address_county": "",
            "home_address_city": "1",
            "home_address_street": "",
            "home_address_house": "",
            "home_address_flat": "",
            "home_address_building": "",
            "visited_country_id": -1,
            "visited_from_date": "",
            "visited_to_date": "",
            "region_id": 1,
            "job": "",
            "job_position": "",
            "job_address_country_id": 88,
            "job_address_state": "",
            "job_address_county": "",
            "job_address_city": "",
            "job_address_street": "",
            "job_address_house": "",
            "job_address_flat": "",
            "job_address_building": "",
            "telephone": "",
            "email": "",
            "is_found": 0,
            "is_infected": 0,
            "is_contacted": 0,
            "create": ""
        }

        rv = self.app.post("/add_person", data=patient, follow_redirects=True)
        assert "patient_id" in str(rv.data)

    def test_edit_patient(self):
        p = Patient.query.filter_by(travel_type_id=3)[-1]
        self.login("adm", "paswd")
        patient = {
            "travel_type": "auto_type",
            "arrival_date": "2020-04-10",
            "auto_border_id": 1,
            "second_name": "test",
            "first_name": "as",
            "patronymic_name": "",
            "gender": -1,
            "dob": "2020-04-17",
            "iin": "",
            "country_of_residence_id": 88,
            "citizenship_id": 88,
            "pass_num": "",
            "home_address_country_id": 88,
            "home_address_state": "",
            "home_address_county": "",
            "home_address_city": "Нур-Султан",
            "home_address_street": "Буктырма",
            "home_address_house": "23",
            "home_address_flat": "",
            "home_address_building": "",
            "visited_country_id": -1,
            "visited_from_date": "",
            "visited_to_date": "",
            "region_id": 1,
            "job": "",
            "job_position": "",
            "job_address_country_id": 88,
            "job_address_state": "",
            "job_address_county": "",
            "job_address_city": "",
            "job_address_street": "",
            "job_address_house": "",
            "job_address_flat": "",
            "job_address_building": "",
            "telephone": "",
            "email": "",
            "is_found": 0,
            "is_infected": 0,
            "is_contacted": 0,
            "create": ""
        }

        # POST /patient_profile?id=2 HTTP/1.1
        rv = self.app.post("/patient_profile?id=" + str(p.id), data=patient, follow_redirects=True)
        assert "Профиль успешно обновлен" in str(rv.data.decode('utf-8'))

    def test_delete_patient(self):
        self.login("adm", "paswd")
        # POST /delete_patient HTTP/1.1
        PATIENT = Patient.query.all()[-1]
        rv = self.app.post("/delete_patient", data={"delete": PATIENT.id}, follow_redirects=True)
        assert "Пользователь успешно удален" in str(rv.data.decode('utf-8'))

        pass

    def test_delete_train(self):
        self.login("adm", "paswd")
        TRAIN = Train.query.all()[-1]
        rv = self.app.post("/delete_train", data={"delete": TRAIN.id}, follow_redirects=True)
        assert "ЖД Рейс успешно удален" in str(rv.data.decode('utf-8'))

    def test_delete_flight(self):
        self.login("adm", "paswd")
        FLIGHT = FlightCode.query.all()[-1]
        rv = self.app.post("/delete_flight", data={"delete": FLIGHT.id}, follow_redirects=True)
        assert "Рейс успешно удален" in str(rv.data.decode('utf-8'))
        pass
    def add_patient(self):
        city = ["Нур-султан", "Алматы"]
        streetsAst = ["Кунаева", "Байтурсынова", "Абая", "Абылайхана"]
        streetsAla = ["Жубанова", "Есенова", "Сарсенбаева", "Янтарная", "Сазановская"]

        n = random.randrange(2)
        c = city[n]
        s = ""
        if n == 0:
            s = streetsAst[random.randrange(4)]
        else:
            s = streetsAla[random.randrange(5)]
        fake = Faker(['ru_RU'])
        profile = fake.profile()
        name = profile["name"]
        iin = profile["ssn"]
        birthdate = profile["birthdate"]
        pass_num = "N{}".format(fake.ssn()[:8])
        patient = {
            "travel_type": "auto_type",
            "arrival_date": "2020-04-10",
            "auto_border_id": 1,
            "second_name": names.get_last_name(),
            "first_name": names.get_first_name(),
            "gender": -1,
            "dob": "2020-04-17",
            "iin": iin,
            "country_of_residence_id": 88,
            "citizenship_id": 88,
            "pass_num": pass_num,
            "home_address_country_id": 88,
            "home_address_state": "",
            "home_address_county": "",
            "home_address_city": c,
            "home_address_street": s,
            "home_address_house": "23",
            "home_address_flat": "",
            "home_address_building": "",
            "visited_country_id": -1,
            "visited_from_date": "",
            "visited_to_date": "",
            "region_id": 1,
            "job": "",
            "job_position": "",
            "job_address_country_id": 88,
            "job_address_state": "",
            "job_address_county": "",
            "job_address_city": "",
            "job_address_street": "",
            "job_address_house": "",
            "job_address_flat": "",
            "job_address_building": "",
            "telephone": "",
            "email": "",
            "is_found": 0,
            "is_infected": 0,
            "is_contacted": 0,
            "create": ""
        }

        return self.app.post("/add_person", data=patient, follow_redirects=True)

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password,
            login=""
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)


if __name__ == '__main__':
    unittest.main()
