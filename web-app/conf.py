import os
import unittest
from config import config_dict
from flask_babelex import Babel

from flask import request, session
from time import sleep
from app import create_app, db

from app.login.util import hash_pass

from app.login.models import User

from app.main.patients.forms import PatientForm, UpdateProfileForm, AddFlightFromExcel

from flask_migrate import Migrate
from sqlalchemy import create_engine


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

    def test_new_patient(self):
        self.login("adm","paswd")
        rv = self.add_post()
        print(str(rv.data))
        assert "patient_id" in str(rv.data)

    def test_edit_patient(self):
        pass

    def test_delete_patient(self):
        pass

    def add_post(self):

        patient = {"travel_type":"auto_type",
        "arrival_date":"2020-04-10",
        "auto_border_id":1,
        "second_name":"str",
        "first_name":"str",
        "patronymic_name":"",
        "gender":-1,
        "dob":"2020-04-03",
        "iin":"",
        "citizenship_id":88,
        "pass_num":"",
        "country_of_residence_id":88,
        "home_address_country_id":88,
        "home_address_state":"",
        "home_address_city":"str",
        "home_address_street":"str",
        "home_address_house":"str",
        "home_address_flat":"",
        "home_address_building":"",
        "visited_country_id":-1,
        "visited_from_date":"",
        "visited_to_date":"",
        "region_id":1,
        "job":"str",
        "job_position":"",
        "job_address_country_id":88,
        "job_address_state":"",
        "job_address_city":"",
        "job_address_street":"",
        "job_address_house":"",
        "job_address_flat":"",
        "job_address_building":"",
        "telephone":"str",
        "email":"",
        "is_found":0,
        "is_infected":0,
        "create":""}

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