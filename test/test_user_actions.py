import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import unittest
from app import app, db, User
from werkzeug.security import generate_password_hash


class TestUserLoginIntegration(unittest.TestCase):
    def setUp(self):
        # Setup the test app
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory database
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Create a test user
            user = User(username="testuser1", password=generate_password_hash("testpassword"), 
                        first_name="Test", last_name="User")
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        # Clean up after each test
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_signup(self):
        # Simulate POST request to sign up
        response = self.client.post('/signup', data=dict(
            username='newuser',
            password='newpassword',
            first_name='New',
            last_name='User'
        ), follow_redirects=True)

        # Check if the user is redirected to login page after signup
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

        # Check if the new user is in the database
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)

    def test_user_login_logout(self):
        # Simulate POST request to log in
        response = self.client.post('/login', data=dict(
            username='testuser',
            password='testpassword'
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # Simulate GET request to log out
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
