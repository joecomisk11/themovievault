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
            user = User(username="testuser", password=generate_password_hash("testpassword"))
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        # Clean up after each test
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_and_dashboard(self):
        # Step 1: Log in the user
        login_response = self.client.post('/login', data=dict(
            username='testuser2',
            password='testpassword'
        ), follow_redirects=True)

        # Check if the login was successful
        self.assertEqual(login_response.status_code, 200)

        # Step 2: Access the dashboard
        dashboard_response = self.client.get('/')
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b'New Movies', dashboard_response.data)

    def test_favorites_button_displayed_for_authenticated_user(self):
        # Log in the user first
        with self.client:
            self.client.post('/login', data=dict(
                username='testuser',
                password='testpassword'
            ), follow_redirects=True)

            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'View Favorite Movies', response.data)
            

if __name__ == '__main__':
    unittest.main()
