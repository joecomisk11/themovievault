import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import unittest
import requests
from unittest.mock import patch, MagicMock, Mock
from app import fetch_movies_by_genre, fetch_top_rated_movies, \
    fetch_movies_by_search, fetch_movie_by_id

class TestFetchMoviesByGenre(unittest.TestCase):

    @patch('requests.get')
    def test_valid_genre(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': ['movie1', 'movie2']}
        mock_get.return_value = mock_response
        genre_name = 'Action'
        result = fetch_movies_by_genre(genre_name)
        self.assertEqual(result, ['movie1', 'movie2'])

    @patch('requests.get')
    def test_invalid_genre(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response
        genre_name = 'Invalid Genre'
        result = fetch_movies_by_genre(genre_name)
        self.assertEqual(result, [])

    @patch('requests.get')
    def test_api_request_failure(self, mock_get):
        mock_get.side_effect = Exception('API request failed')
        genre_name = 'Action'
        with self.assertRaises(Exception):
            fetch_movies_by_genre(genre_name)

    @patch('requests.get')
    def test_api_request_success_no_results(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        genre_name = 'Action'
        result = fetch_movies_by_genre(genre_name)
        self.assertEqual(result, [])

    @patch('requests.get')
    def test_valid_query(self, mock_get):
        mock_response = MagicMock()
        # Add 'poster_path' to the result
        mock_response.json.return_value = {
            'results': [{'title': 'Movie 1', 'poster_path': '/path/to/poster1.jpg'}]
        }
        mock_get.return_value = mock_response

        query = 'valid query'
        results = fetch_movies_by_search(query)

        # Expected result should only include movies with a poster
        expected_results = [{'title': 'Movie 1', 'poster_path': '/path/to/poster1.jpg'}]
        self.assertEqual(results, expected_results)


    @patch('requests.get')
    def test_empty_query(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response
        query = ''
        results = fetch_movies_by_search(query)
        self.assertEqual(results, [])

    @patch('requests.get')
    def test_no_results(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response
        query = 'no results'
        results = fetch_movies_by_search(query)
        self.assertEqual(results, [])

    @patch('requests.get')
    def test_multiple_results(self, mock_get):
        mock_response = MagicMock()
        # Add 'poster_path' to each result
        mock_response.json.return_value = {
            'results': [
                {'title': 'Movie 1', 'poster_path': '/path/to/poster1.jpg'},
                {'title': 'Movie 2', 'poster_path': '/path/to/poster2.jpg'}
            ]
        }
        mock_get.return_value = mock_response

        query = 'multiple results'
        results = fetch_movies_by_search(query)

        # Expected result should only include movies with a poster
        expected_results = [
            {'title': 'Movie 1', 'poster_path': '/path/to/poster1.jpg'},
            {'title': 'Movie 2', 'poster_path': '/path/to/poster2.jpg'}
        ]
        self.assertEqual(results, expected_results)

    @patch('requests.get')
    def test_request_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException
        query = 'exception query'
        with self.assertRaises(requests.exceptions.RequestException):
            fetch_movies_by_search(query)

    @patch('requests.get')
    def test_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(requests.exceptions.ConnectionError):
            fetch_top_rated_movies()

    @patch('requests.get')
    def test_invalid_response_format(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {'error': 'Invalid response format'}
        mock_get.return_value = mock_response
        result = fetch_top_rated_movies()
        self.assertEqual(result, [])

    @patch('requests.get')
    def test_successful_api_call(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 123, 'title': 'Test Movie'}
        mock_get.return_value = mock_response

        result = fetch_movie_by_id(123)

        self.assertEqual(result, {'id': 123, 'title': 'Test Movie'})

    @patch('requests.get')
    def test_invalid_movie_id(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        result = fetch_movie_by_id(123)
        self.assertIsNone(result)

    @patch('requests.get')
    def test_api_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException
        result = fetch_movie_by_id(123)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
