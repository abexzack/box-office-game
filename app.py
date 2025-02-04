from flask import Flask, render_template, jsonify, request
from movie_data import MovieDataService, TMDBError
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

try:
    # Initialize with access token from .env
    movie_service = MovieDataService()
except ValueError as e:
    print(f"Error initializing MovieDataService: {e}")
    print("Please ensure TMDB_TOKEN is set in your .env file")
    exit(1)

@app.route('/')
def home():
    movies = movie_service.get_actor_movies("Tom Hanks")
    return render_template('home.html', actor_name="Tom Hanks", movies=movies)

@app.route('/new_game')
def new_game():
    return home()  # For now, just redirect to home with a fresh state

@app.route('/search_movies')
def search_movies():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    try:
        movies = movie_service.search_movies(query)
        return jsonify(movies)
    except TMDBError as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True) 