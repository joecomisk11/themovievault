import os

import requests
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, \
    logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

app = Flask(__name__, template_folder=os.path.abspath('../templates'))

app.config['SECRET_KEY'] = 'bgfbrbg843thu34iingubdf'
OMDB_API_KEY = ' b54b0bbd'
TMDB_API_KEY = '056f3d31df0856f08c488274990e7921'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
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
    movie = fetch_movie_details(title)
    if not movie:
        flash("Movie not found")
        return redirect(url_for('dashboard'))

    cast = movie.get('credits', {}).get('cast', [])[:10]  # Fetch cast members
    movie_details = {
        'title': movie.get('title', 'N/A'),
        'release_date': movie.get('release_date', 'N/A'),
        'poster_path': movie.get('poster_path', None),
        'genres': movie.get('genres', []),
        'vote_average': movie.get('vote_average', 'N/A'),
        'runtime': movie.get('runtime', 'N/A'),
        'overview': movie.get('overview', 'N/A'),
    }
    return render_template('movie.html', movie=movie_details, cast=cast)

@app.route('/search', methods=['GET'])
def search_movies():
    query = request.args.get('query')
    if query:
        search_results = fetch_movies_by_search(query)
    else:
        search_results = []
    return render_template('search_results.html', search_results=search_results, query=query)

def fetch_new_movies():
    url = f"https://api.themoviedb.org/3/movie/now_playing?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    return response.json().get('results', [])

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

if __name__ == "__main__":
    app.run(debug=True)