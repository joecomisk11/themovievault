import sys
import os
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import unittest
from app import app, db, User, Favorite
from werkzeug.security import generate_password_hash


class TestFavoritesIntegration(unittest.TestCase):
    def setUp(self):
        # Setup the test app
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Create a test user
            user = User(username="testuser3",
                        password=generate_password_hash("testpassword"),
                        first_name="Test", last_name="User")
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        # Clean up after each test
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_add_to_favorites_and_view(self):
        # Log in the user first
        self.client.post('/login', data=dict(
            username='testuser3',
            password='testpassword'
        ), follow_redirects=True)

        # Add a movie to favorites
        add_favorite_response = self.client.post('/add_to_favorites/550',
                                                 follow_redirects=True)
        self.assertEqual(add_favorite_response.status_code, 200)

        # View favorites
        favorites_response = self.client.get('/favorites')
        self.assertEqual(favorites_response.status_code, 200)
        self.assertIn(b'Fight Club', favorites_response.data)

    @patch('app.fetch_movie_by_id')
    def test_add_to_favorites(self, mock_fetch_movie):
        with app.app_context():  # Push the application context

            # Mock the movie details returned from the API
            mock_fetch_movie.return_value = {
                'id': 550,
                'title': 'Fight Club',
                'poster_path': '/poster.jpg',
                'release_date': '1999-10-15',
                'vote_average': 8.4,
                'runtime': 139
            }

            # Log the user in first
            self.client.post('/login', data=dict(
                username='testuser',
                password='testpassword'
            ), follow_redirects=True)

            # Simulate POST request to add a movie to favorites
            response = self.client.post('/add_to_favorites/550',
                                        follow_redirects=True)

            self.assertEqual(response.status_code, 200)

    @patch('app.fetch_movie_by_id')
    def test_remove_from_favorites(self, mock_fetch_movie):
        # Mock the movie details returned from the API
        mock_fetch_movie.return_value = {
            'id': 550,
            'title': 'Fight Club',
            'poster_path': '/poster.jpg',
            'release_date': '1999-10-15',
            'vote_average': 8.4,
            'runtime': 139
        }

        # Log the user in first
        self.client.post('/login', data=dict(
            username='testuser',
            password='testpassword'
        ), follow_redirects=True)

        # Simulate POST request to add a movie to favorites
        self.client.post('/add_to_favorites/550', follow_redirects=True)

        # Simulate POST request to remove the movie from favorites
        response = self.client.post('/remove_from_favorites/550',
                                    follow_redirects=True)

        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
