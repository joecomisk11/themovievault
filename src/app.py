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
    from models import db, User, Favorite  # Local import
except ModuleNotFoundError:
    from src.models import db, User, Favorite  # Heroku import

app = Flask(__name__)

sentry_sdk.init(
    dsn="https://a6dac84ec65d0d4edc43a70edf1674c4@o4508120998936576.ingest.us.sentry.io/4508121009815552",
    integrations=[FlaskIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0
)


app.config['SECRET_KEY'] = 'bgfbrbg843thu34iingubdf'
OMDB_API_KEY = ' b54b0bbd'
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
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
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
    logout_user()
    return redirect(url_for('dashboard'))


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Get updated information from the form
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        new_password = request.form.get('password')
        
        # Check if the user wants to change their password
        if new_password:
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            current_user.password = hashed_password
        
        # Commit changes to the database
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except OperationalError:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')

    # Render the edit profile page
    return render_template('edit_profile.html')


def fetch_popular_movies_tmdb():
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
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    search_response = requests.get(search_url)
    search_data = search_response.json()

    if search_data['results']:
        movie_id = search_data['results'][0]['id']
        # Fetch detailed movie info by ID
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
        movie_response = requests.get(details_url)
        movie_details = movie_response.json()

        return movie_details
    return {}


@app.route('/movie/<title>')
def movie_details(title):
    movie = fetch_movie_details(title)  # Fetch movie by title

    if not movie:
        flash("Movie not found")
        return redirect(url_for('dashboard'))

    cast = movie.get('credits', {}).get('cast', [])[:10]

    # Check if the movie is already in the user's favorites
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
    favorite = Favorite.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash("Movie has been removed from your favorites.", "success")

    return redirect(url_for('movie_details', title=fetch_movie_by_id(movie_id)['title']))


@app.route('/favorites')
@login_required
def view_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', favorites=favorites)


@app.route('/recommendations')
@login_required
def recommendations():
    genre_recommendations, actor_recommendations = fetch_recommendations()
    return render_template('recommendations.html', 
                           genre_recommendations=genre_recommendations, 
                           actor_recommendations=actor_recommendations)


def fetch_new_movies():
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
            return None  # Return None if the movie is not found (e.g., 404)
    except requests.exceptions.RequestException:
        return None   # Return None if the movie is not found


def fetch_top_rated_movies():
    url = f"https://api.themoviedb.org/3/movie/top_rated?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    return response.json().get('results', [])


def fetch_movies_by_genre(genre_name):
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
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    response = requests.get(url)
    return response.json().get('results', [])


def get_user_favorites():
    """Fetch the current user's favorite movies and extract genres and actors."""
    favorite_movies = Favorite.query.filter_by(user_id=current_user.id).all()

    if not favorite_movies:
        return None, None

    genres = []
    actors = []

    for favorite in favorite_movies:
        # Fetch movie details by movie ID from the TMDb API
        movie_details = fetch_movie_by_id(favorite.movie_id)

        # Add genres from the movie details to the list
        if 'genres' in movie_details:
            genres.extend([genre['name'] for genre in movie_details['genres']])

        # Add top 3 actors from the movie to the list
        if 'credits' in movie_details:
            actors.extend([actor['name'] for actor in movie_details['credits']['cast'][:3]])

    print(f"Collected genres: {genres}")  # Add this line to print collected genres
    return genres, actors



def fetch_recommendations():
    """Fetch recommended movies based on user's favorite genres or actors."""
    genres, actors = get_user_favorites()
    print(f"Genres: {genres}")  # Check if genres are correctly collected
    print(f"Actors: {actors}")

    genre_recommendations = []
    actor_recommendations = []

    if genres:
        # Get the most common genre
        common_genre = Counter(genres).most_common(1)[0][0]
        print(f"Most common genre: {common_genre}")  # Print the most common genre
        genre_recommendations.extend(fetch_movies_by_genre(common_genre))

    if actors:
        # Get the most common actor
        common_actor = Counter(actors).most_common(1)[0][0]
        print(f"Most common actor: {common_actor}")  # Print the most common actor
        actor_recommendations.extend(fetch_movies_by_actor(common_actor))

    # Remove duplicate recommendations
    unique_genre_recommendations = {movie['id']: movie for movie in genre_recommendations}.values()
    unique_actor_recommendations = {movie['id']: movie for movie in actor_recommendations}.values()

    return list(unique_genre_recommendations), list(unique_actor_recommendations)


def fetch_movies_by_actor(actor_name):
    """Fetch movies from TMDb API based on actor."""
    url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={actor_name}"
    response = requests.get(url)
    actor_data = response.json()

    if actor_data['results']:
        actor_id = actor_data['results'][0]['id']
        # Fetch movies featuring the actor by their ID
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_cast={actor_id}"
        response = requests.get(url)
        return response.json().get('results', [])

    return []

def fetch_movies_by_genre(genre_name):
    """Fetch movies from TMDb API based on genre."""
    genre_map = {
        'Action': 28,
        'Comedy': 35,
        'Horror': 27,
        'Romance': 10749,
        'Science Fiction': 878,  # Added Science Fiction
        'Thriller': 53,          # Added Thriller
        'Drama': 18,             # Added Drama
        'Adventure': 12          # Added Adventure
    }
    genre_id = genre_map.get(genre_name)
    if genre_id:
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&language=en-US&page=1"
        response = requests.get(url)
        print(f"Fetching movies for genre: {genre_name}")  # Debugging print statement
        print(f"API response: {response.json()}")  # Print the API response for debugging
        return response.json().get('results', [])
    else:
        print(f"Genre {genre_name} not found in genre_map.")
        return []




if __name__ == "__main__":
    app.run(debug=True)
