import unittest
from unittest.mock import patch
from app import app, db
from models import User
from flask import session
from werkzeug.security import generate_password_hash

class TestMovieDetailsIntegration(unittest.TestCase):

    def setUp(self):
        # Set up the app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory database
        self.app = app
        self.client = app.test_client()

        # Create an application context
        with self.app.app_context():
            db.create_all()

            # Create a test user
            test_user = User(
                username='testuser4',
                password=generate_password_hash('testpassword', method='pbkdf2:sha256'),
                first_name='Test',
                last_name='User'
            )
            db.session.add(test_user)
            db.session.commit()

            self.user = test_user

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('app.fetch_movie_details')
    def test_movie_details(self, mock_fetch_details):
        # Mock the movie details returned from the API
        mock_fetch_details.return_value = {
            'id': 550,
            'title': 'Fight Club',
            'poster_path': '/poster.jpg',
            'release_date': '1999-10-15',
            'genres': [{'name': 'Drama'}, {'name': 'Thriller'}],
            'vote_average': 8.4,
            'runtime': 139,
            'overview': 'A ticking-time-bomb insomniac and a soap salesman...',
            'credits': {'cast': [{'name': 'Brad Pitt'}, {'name': 'Edward Norton'}]}
        }

        # Simulate GET request to the movie details page
        response = self.client.get('/movie/Fight Club')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Fight Club', response.data)
        self.assertIn(b'Brad Pitt', response.data)

if __name__ == '__main__':
    unittest.main()
