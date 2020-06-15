#Unit test for application.py

# !!! test methods must begin with test_...
# To run this script i=from a terminal: python -m unittest test_application.py

import unittest
from books_app import app

class TestBooksApp(unittest.TestCase):

    def test_login_loads(self):                             # test the login route function
        with app.test_client() as client:             # NOTE: URL response code 200 means OK
            response = client.get('/login', content_type = 'html/text')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b'Please login' in response.data)

    def test_index(self):                                   # test the login route function
        with app.test_client() as client:              # NOTE: Check text on login page in response
            response = client.get('/', content_type = 'html/text')
            self.assertEqual(response.status_code, 302)  # test for redirect to login page (not logged in))

    def test_index_requires_login(self):                                   # test the login route function
        with app.test_client() as client:              # NOTE: Check text on login page in response
            response = client.get('/', follow_redirects = True)
            self.assertTrue(b'Please login first' in response.data)  # test for request to login

    def test_good_login(self):                                   # test the login with correct credentials
        tester = app.test_client(self)
        response = tester.post('/login', data =dict(username="admin", password="admin"), follow_redirects=True)
        self.assertTrue(b'logged in' in response.data)  # check for flash message of logged in
        self.assertEqual(response.status_code, 200)

    def test_bad_login(self):                                   # test an invalid login
        tester = app.test_client(self)
        response = tester.post('/login', data =dict(username="admininstrator", password="blahblah"), follow_redirects=True)
        self.assertTrue(b'User name or password not found. Please try again' in response.data)  # check for flash message text
        self.assertEqual(response.status_code, 200)

    def test_logout(self):                                   # test logout page
        tester = app.test_client(self)
        response = tester.get('/logout', content_type = 'html/text', follow_redirects=True)
        self.assertTrue(b'logged out' in response.data)  # check for flash message text
        self.assertTrue(b'Please login' in response.data)  # back to login page ?

if __name__ == '__main__':
    unittest.main()
