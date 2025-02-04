from flask import Flask, render_template, jsonify, request, session
from movie_data import MovieDataService, TMDBError
import os
from dotenv import load_dotenv
from typing import Tuple, List, Dict
import random

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-this')  # Add to .env

# List of actors to randomly select from
ACTOR_POOL = [
    "Tom Hanks", "Morgan Freeman", "Leonardo DiCaprio", "Meryl Streep",
    "Brad Pitt", "Julia Roberts", "Denzel Washington", "Sandra Bullock"
]

try:
    movie_service = MovieDataService()
except ValueError as e:
    print(f"Error initializing MovieDataService: {e}")
    print("Please ensure TMDB_TOKEN is set in your .env file")
    exit(1)

def init_game_state(actor_name: str) -> Tuple[List[Dict], List[str]]:
    """Initialize game state with actor's movies and their details"""
    movies = movie_service.get_actor_movies_with_details(actor_name)
    movie_ids = [str(movie['id']) for movie in movies]
    return movies, movie_ids

@app.route('/start_game')
def start_game():
    """Initialize a new game with a random actor"""
    try:
        # Select random actor
        actor_name = random.choice(ACTOR_POOL)
        
        # Get actor's movies and initialize game state
        correct_movies, movie_ids = init_game_state(actor_name)
        
        # Set up session state
        session['actor_name'] = actor_name
        session['correct_movie_ids'] = movie_ids
        session['correct_movies'] = correct_movies
        session['guessed_movies'] = []
        session['strikes'] = 0
        session['game_over'] = False
        
        return jsonify({
            'actor_name': actor_name,
            'message': 'New game started!',
            'strikes': 0,
            'game_over': False
        })
    
    except TMDBError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    """Handle movie guess submission"""
    if 'actor_name' not in session:
        return jsonify({'error': 'No active game'}), 400
    
    if session.get('game_over'):
        return jsonify({'error': 'Game is over'}), 400
    
    movie_id = request.json.get('movie_id')
    if not movie_id:
        return jsonify({'error': 'No movie_id provided'}), 400
    
    # Convert to string for comparison
    movie_id = str(movie_id)
    correct_movies = session['correct_movies']
    guessed_movies = session['guessed_movies']
    
    # Check if movie already guessed
    if movie_id in [m['id'] for m in guessed_movies]:
        return jsonify({'error': 'Movie already guessed'}), 400
    
    # Get movie details
    try:
        movie_details = movie_service.get_movie_details(movie_id)
    except TMDBError as e:
        return jsonify({'error': str(e)}), 500
    
    # Check if guess is correct
    is_correct = movie_id in session['correct_movie_ids']
    
    if is_correct:
        guessed_movies.append(movie_details)
        session['guessed_movies'] = guessed_movies
        
        # Check if all movies found
        if len(guessed_movies) == len(correct_movies):
            session['game_over'] = True
            return jsonify({
                'correct': True,
                'message': 'Congratulations! You found all movies!',
                'game_over': True,
                'guessed_movies': guessed_movies,
                'strikes': session['strikes']
            })
    else:
        session['strikes'] = session['strikes'] + 1
        if session['strikes'] >= 3:
            session['game_over'] = True
            return jsonify({
                'correct': False,
                'message': 'Game Over! Too many incorrect guesses.',
                'game_over': True,
                'correct_movies': correct_movies,
                'strikes': session['strikes']
            })
    
    return jsonify({
        'correct': is_correct,
        'message': 'Correct guess!' if is_correct else 'Incorrect guess!',
        'guessed_movies': guessed_movies,
        'strikes': session['strikes'],
        'game_over': session['game_over']
    })

@app.route('/')
def home():
    # Start new game if none active
    if 'actor_name' not in session:
        start_game()
    
    return render_template('home.html', 
                         actor_name=session['actor_name'],
                         strikes=session['strikes'],
                         guessed_movies=session['guessed_movies'],
                         game_over=session['game_over'])

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