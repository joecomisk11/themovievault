from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    favorites = db.relationship('Favorite', backref='user', lazy=True)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)
    movie_title = db.Column(db.String(255), nullable=False)
    movie_poster = db.Column(db.String(255), nullable=False)
    movie_release_date = db.Column(db.String(255), nullable=False)
    movie_rating = db.Column(db.Float, nullable=False)
    movie_runtime = db.Column(db.Integer, nullable=False)
