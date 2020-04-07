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
        # response = self.login("eror", "s")
        # self.assertEqual(response.status_code, 200)
        # print(str(rv.data.decode('utf-8')))

        rv = self.login('adm', 'paswd')
        assert 'Dashboard' in str(rv.data)
        rv = self.logout()
        assert 'Login' in str(rv.data)
        rv = self.login('adm', 'Wrong')
        assert 'Wrong' in str(rv.data)
        rv = self.login('admin', 'paswd')
        assert 'Wrong' in str(rv.data)

    def test_new_patient(self):
        patient = PatientForm()
        patient.travel_type="railway_type"
        patient.arrival_date="2020-04-29"
        patient.first_name="a"
        patient.second_name="a"
        patient.patronymic_name="a"
        patient.gender="-1"
        patient.dob="2020-04-08"
        patient.iin="12121212121212"
        patient.citizenship_id=88
        patient.pass_num="12121212"
        patient.country_of_residence_id=88
        patient.home_address_country_id=88
        patient.home_address_state="2"
        patient.home_address_city="2"
        patient.home_address_street="12"
        patient.home_address_house="12"
        patient.home_address_flat="22"
        patient.home_address_building="2"
        patient.visited_country_id=8
        patient.visited_from_date="2020-03-31"
        patient.visited_to_date="2020-04-15"
        patient.region_id=1
        patient.job="12"
        patient.job_position="12"
        patient.job_address_country_id=88
        patient.job_address_state="12"
        patient.job_address_city="12"
        patient.job_address_street="12"
        patient.job_address_house="12"
        patient.job_address_flat="12"
        patient.job_address_building="112"
        patient.telephone="1212"
        patient.email="2@gmail.com"
        patient.is_found=0
        patient.is_infected=0
        patient.create=""

        rv = self.app.post("/add_patient", data=patient, follow_redirect=True)
        print(str(rv.data.decode('utf-8')))
        pass

    def test_edit_patient(self):
        pass

    def test_delete_patient(self):
        pass


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