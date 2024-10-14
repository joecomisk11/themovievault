import os
import requests
from flask import Flask, render_template, redirect, url_for, request, flash
from sqlalchemy.exc import OperationalError
from flask_login import LoginManager, login_user, login_required, \
    logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from collections import Counter
try:
    from models import db, User, Favorite
except ModuleNotFoundError:
    from src.models import db, User, Favorite

app = Flask(__name__)

sentry_sdk.init(
    dsn="https://a6dac84ec65d0d4edc43a70edf1674c4@o4508120998936576.ingest.us.sentry.io/4508121009815552",
    integrations=[FlaskIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0
)


app.config['SECRET_KEY'] = 'bgfbrbg843thu34iingubdf'
TMDB_API_KEY = '056f3d31df0856f08c488274990e7921'

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    try:
        db.create_all()
    except OperationalError:
        print("Tables already exist. Skipping creation.")


@login_manager.user_loader
def load_user(user_id):
    """
    Callback function for Flask-Login to load a user by their ID.

    Args:
        user_id: The ID of the user to load.

    Returns:
        The User object associated with the given ID.
    """
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles the login process by checking the given username and password against
    the database of registered users. If the credentials are valid, the user is
    logged in and redirected to the dashboard. Otherwise, an error message is
    flashed to the user.

    GET: Displays the login form.

    POST: Handles the login form submission.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('Invalid username or password')

        elif check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        else:
            flash('Invalid username or password')

    return render_template('login.html', hide_login=True)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Handles the signup process by validating the given username and password
    against the database of registered users, and if valid, creates a new user
    and redirects to the login page.

    GET: Displays the signup form.

    POST: Handles the signup form submission.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        new_user = User(username=username, password=hashed_password,
                        first_name=first_name, last_name=last_name)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html', hide_login=True)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """
    Logs out the current user and redirects to the dashboard.

    GET: Redirects to the dashboard.

    POST: Logs out the current user and redirects to the dashboard.
    """
    logout_user()
    return redirect(url_for('dashboard'))


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Handles the edit profile form submission.

    GET: Displays the edit profile form.

    POST: Updates the current user's information from the form and redirects to the dashboard.
    """
    if request.method == 'POST':
        # Get updated information from the form
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        new_password = request.form.get('password')

        if new_password:
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            current_user.password = hashed_password

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except OperationalError:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')

    return render_template('edit_profile.html')


def fetch_popular_movies_tmdb():
    """
    Fetches a list of popular movies from The Movie Database API.

    Returns a list of dictionaries with the following keys:
        id: The ID of the movie.
        title: The title of the movie.
        year: The year the movie was released.
        poster: The URL of the movie's poster image.
        overview: A short summary of the movie's plot.
        rating: The average rating of the movie from 0 to 10.
    """
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    movies = []
    if response.status_code == 200:
        data = response.json()
        for movie in data['results']:
            movies.append({
                'id': movie['id'],
                'title': movie['title'],
                'year': movie['release_date'][:4],
                'poster': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                'overview': movie['overview'],
                'rating': movie['vote_average']
            })
    return movies


@app.route('/')
def dashboard():
    """
    Displays the dashboard page.

    The dashboard page contains a list of the newest movies, a list of the top rated movies, and a list of movies for each of the following genres: Action, Comedy, Horror, and Romance.

    Returns a rendered template of the dashboard page.
    """
    new_movies = fetch_new_movies()
    top_rated_movies = fetch_top_rated_movies()
    action_movies = fetch_movies_by_genre('Action')
    comedy_movies = fetch_movies_by_genre('Comedy')
    horror_movies = fetch_movies_by_genre('Horror')
    romance_movies = fetch_movies_by_genre('Romance')

    return render_template(
        'dashboard.html',
        new_movies=new_movies,
        top_rated_movies=top_rated_movies,
        action_movies=action_movies,
        comedy_movies=comedy_movies,
        horror_movies=horror_movies,
        romance_movies=romance_movies
    )


def fetch_movie_details(title):
    """
    Fetches detailed movie information from the TMDb API for the given movie title.
    Returns a dictionary containing the detailed movie information, if found. Otherwise, returns an empty dictionary.
    """
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    search_response = requests.get(search_url)
    search_data = search_response.json()

    if search_data['results']:
        movie_id = search_data['results'][0]['id']
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        movie_response = requests.get(details_url)
        movie_details = movie_response.json()

        return movie_details
    return {}


@app.route('/movie/<title>')
def movie_details(title):
    """
    Displays detailed information about the given movie title, including its
    title, release date, poster, genres, vote average, runtime, and overview.
    If the movie is not found, the user is redirected to the dashboard with a
    message flashed.
    Additionally, if the user is authenticated, the page will display whether
    the movie is already in their favorites or not.
    """
    movie = fetch_movie_details(title)

    if not movie:
        flash("Movie not found")
        return redirect(url_for('dashboard'))

    cast = movie.get('credits', {}).get('cast', [])[:10]

    is_favorite = False
    if current_user.is_authenticated:
        favorite = Favorite.query.filter_by(user_id=current_user.id, movie_id=movie['id']).first()
        is_favorite = True if favorite else False

    movie_details = {
        'id': movie.get('id', 'N/A'),
        'title': movie.get('title', 'N/A'),
        'release_date': movie.get('release_date', 'N/A'),
        'poster_path': movie.get('poster_path', None),
        'genres': movie.get('genres', []),
        'vote_average': movie.get('vote_average', 'N/A'),
        'runtime': movie.get('runtime', 'N/A'),
        'overview': movie.get('overview', 'N/A'),
    }

    return render_template('movie.html', movie=movie_details, cast=cast, is_favorite=is_favorite)


@app.route('/search', methods=['GET'])
def search_movies():
    """
    Displays a list of movies and actors that match the given search query.
    If no query is given, the page is empty.
    """
    query = request.args.get('query')
    if query:
        search_results = fetch_movies_by_search(query)
    else:
        search_results = []
    return render_template('search_results.html', search_results=search_results, query=query)


@app.route('/add_to_favorites/<int:movie_id>', methods=['POST'])
@login_required
def add_to_favorites(movie_id):
    # Fetch movie details by movie_id
    """
    Adds a movie to the user's favorites.

    Args:
        movie_id (int): The ID of the movie to add to the user's favorites.

    Returns:
        Redirects to the movie's details page.
    """
    movie = fetch_movie_by_id(movie_id)

    if movie:
        favorite = Favorite(
            user_id=current_user.id,
            movie_id=movie['id'],
            movie_title=movie['title'],
            movie_poster=movie['poster_path'],
            movie_release_date=movie['release_date'],
            movie_rating=movie['vote_average'],
            movie_runtime=movie['runtime']
        )

        db.session.add(favorite)
        db.session.commit()
        flash(f"{movie['title']} has been added to your favorites!", "success")

    return redirect(url_for('movie_details', title=movie['title']))


@app.route('/remove_from_favorites/<int:movie_id>', methods=['POST'])
@login_required
def remove_from_favorites(movie_id):
    # Find the favorite entry
    """
    Removes a movie from the user's favorites.

    Args:
        movie_id (int): The ID of the movie to remove from the user's favorites.

    Returns:
        Redirects to the movie's details page.
    """
    favorite = Favorite.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash("Movie has been removed from your favorites.", "success")

    return redirect(url_for('movie_details', title=fetch_movie_by_id(movie_id)['title']))


@app.route('/favorites')
@login_required
def view_favorites():
    """
    Displays the user's favorite movies.

    Returns:
        A rendered template of the user's favorite movies.
    """
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', favorites=favorites)


@app.route('/recommendations')
@login_required
def recommendations():
    """
    Displays recommended movies based on the user's favorite genres or actors.

    Returns:
        A rendered template with recommended movies.
    """
    genre_recommendations, actor_recommendations = fetch_recommendations()
    return render_template('recommendations.html',
                           genre_recommendations=genre_recommendations, 
                           actor_recommendations=actor_recommendations)


def fetch_new_movies():
    """
    Fetches a list of currently playing movies from the TMDb API.

    Returns a list of dictionaries with the following keys:
        id: The ID of the movie.
        title: The title of the movie.
        year: The year the movie was released.
        poster: The URL of the movie's poster image.
        overview: A short summary of the movie's plot.
        rating: The average rating of the movie from 0 to 10.
    """
    url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    return response.json().get('results', [])


def fetch_movie_by_id(movie_id):
    """
    Fetches movie details from TMDb API based on the movie ID.
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            movie_details = response.json()
            return movie_details
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def fetch_top_rated_movies():
    """
    Fetches a list of top-rated movies from the TMDb API.

    Returns a list of dictionaries with the following keys:
        id: The ID of the movie.
        title: The title of the movie.
        year: The year the movie was released.
        poster: The URL of the movie's poster image.
        overview: A short summary of the movie's plot.
        rating: The average rating of the movie from 0 to 10.
    """
    url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    return response.json().get('results', [])


def fetch_movies_by_genre(genre_name):
    """
    Fetches a list of movies by genre from the TMDb API.

    The supported genres are: Action, Comedy, Horror, Romance.

    Args:
        genre_name (str): The name of the genre to fetch movies for.

    Returns:
        A list of dictionaries containing the movie details, if found. Otherwise, returns an empty list.
    """
    genre_map = {
        'Action': 28,
        'Comedy': 35,
        'Horror': 27,
        'Romance': 10749
    }
    genre_id = genre_map.get(genre_name)
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&language=en-US&page=1"
    response = requests.get(url)
    return response.json().get('results', [])


def fetch_movies_by_search(query):
    # Search for movies by title
    """
    Searches for movies by title or actor name in the TMDb API.

    If the search query is a movie title, it will return a list of movies with a matching title.
    If the search query is an actor name, it will return a list of movies featuring that actor.

    Args:
        query (str): The search query to pass to the TMDb API.

    Returns:
        A list of dictionaries containing the movie details, if found. Otherwise, returns an empty list.
    """
    movie_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    movie_response = requests.get(movie_url)
    movie_results = movie_response.json().get('results', [])

    movie_results = [movie for movie in movie_results if movie.get('poster_path')]

    actor_url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={query}"
    actor_response = requests.get(actor_url)
    actor_results = actor_response.json().get('results', [])

    actor_movie_results = []
    for actor in actor_results:
        for movie in actor.get('known_for', []):
            if movie.get('title') and movie.get('id') and movie.get('poster_path'):
                actor_movie_results.append(movie)

    combined_results = movie_results + actor_movie_results

    return combined_results


def get_user_favorites():
    """
    Collects the genres and actors from the user's favorite movies.

    This function fetches the movie details for each favorite movie, and then
    collects the genres and top 3 actors for each movie. The results are returned
    as two lists: genres and actors.

    Args:
        None

    Returns:
        A tuple of two lists: genres and actors. If the user has no favorite movies,
        the function returns (None, None).
    """
    favorite_movies = Favorite.query.filter_by(user_id=current_user.id).all()

    if not favorite_movies:
        return None, None

    genres = []
    actors = []

    for favorite in favorite_movies:
        movie_details = fetch_movie_by_id(favorite.movie_id)

        if 'genres' in movie_details:
            genres.extend([genre['name'] for genre in movie_details['genres']])

        if 'credits' in movie_details:
            actors.extend([actor['name'] for actor in movie_details['credits']['cast'][:3]])

    return genres, actors



def fetch_recommendations():
    """
    Fetches movie recommendations based on the user's favorite movies.

    This function fetches the user's favorite movies, extracts the genres and actors
    from those movies, and then fetches more movies from the TMDb API based on the
    most common genre and actor.

    Returns a tuple of two lists: the first list contains movies recommended based
    on the user's favorite genres, and the second list contains movies recommended
    based on the user's favorite actors.

    If the user has no favorite movies, the function returns two empty lists.
    """
    genres, actors = get_user_favorites()

    genre_recommendations = []
    actor_recommendations = []

    if genres:
        common_genre = Counter(genres).most_common(1)[0][0]
        genre_recommendations.extend(fetch_movies_by_genre(common_genre))

    if actors:
        common_actor = Counter(actors).most_common(1)[0][0]
        actor_recommendations.extend(fetch_movies_by_actor(common_actor))

    unique_genre_recommendations = {movie['id']: movie for movie in genre_recommendations}.values()
    unique_actor_recommendations = {movie['id']: movie for movie in actor_recommendations}.values()

    return list(unique_genre_recommendations), list(unique_actor_recommendations)


def fetch_movies_by_actor(actor_name):
    """
    Fetches movies from TMDb API based on actor name.

    This function takes an actor name as input, searches for the actor in the TMDb API,
    and then fetches movies featuring that actor by their ID.

    Args:
        actor_name (str): The name of the actor to search for.

    Returns:
        A list of movie dictionaries if found, otherwise an empty list.
    """
    url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={actor_name}"
    response = requests.get(url)
    actor_data = response.json()

    if actor_data['results']:
        actor_id = actor_data['results'][0]['id']
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_cast={actor_id}"
        response = requests.get(url)
        return response.json().get('results', [])

    return []

def fetch_movies_by_genre(genre_name):
    """
    Fetches movies from TMDb API based on genre name.

    This function takes a genre name as input, maps it to its corresponding ID
    in the TMDb API, and then fetches movies from the API based on the genre ID.

    Args:
        genre_name (str): The name of the genre to search for.

    Returns:
        A list of movie dictionaries if found, otherwise an empty list.
    """
    genre_map = {
        'Action': 28,
        'Comedy': 35,
        'Horror': 27,
        'Romance': 10749,
        'Science Fiction': 878,
        'Thriller': 53,
        'Drama': 18,
        'Adventure': 12
    }
    genre_id = genre_map.get(genre_name)
    if genre_id:
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&language=en-US&page=1"
        response = requests.get(url)
        return response.json().get('results', [])
    else:
        return []


if __name__ == "__main__":
    app.run(debug=True)
