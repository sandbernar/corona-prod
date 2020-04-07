import os
import unittest
from config import config_dict

from time import sleep
from app import create_app, db

class TestCase(unittest.TestCase):
    def setUp(self):
        app = create_app(config_dict['Debug'], unittest=True)
        app_ctx = app.app_context()
        app_ctx.push()
       
        self.app = app.test_client()
    
    def tearDown(self):
        db.session.close()
        db.drop_all()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def test_empty_db(self):
        rv = self.app.get('/', follow_redirects=True)
        self.assertIn('div', rv.data)
# 
        # print("br", rv)
        # assert 1 == 1

    # def test_login(self): 
    #     rv = self.login("test", "test")
    #     assert b'You were logged in' in rv.data

    def test_base(self):
        assert 1 == 1


if __name__ == '__main__':
    unittest.main()
# def base_client():
#     app = create_app(config_dict['Debug'])
#     app_ctx = app.app_context()
#     app_ctx.push()
#     db.session.close()
#     db.drop_all()
#     yield app.test_client()