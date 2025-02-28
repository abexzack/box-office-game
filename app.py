from flask import Flask, render_template, jsonify, request, session
from movie_data import MovieDataService, TMDBError
from db_service import DatabaseService
import os
from dotenv import load_dotenv
import random
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-this')

# Initialize services
movie_service = MovieDataService()
db_service = DatabaseService()

@app.route('/start_game')
def start_game():
    """Initialize a new game with a random actor"""
    try:
        # Get random actor from database
        actor = db_service.get_random_actor()
        if not actor:
            logger.error("No actors found in database")
            return jsonify({'error': 'No actors found in database. Please ensure database is populated.'}), 500
        
        # Get actor's movies from database
        movies = db_service.get_actor_movies(actor.name)
        if not movies:
            logger.error(f"No movies found for actor: {actor.name}")
            return jsonify({'error': f'No movies found for actor: {actor.name}'}), 500
        
        movie_ids = [str(movie['id']) for movie in movies]
        # Set up session state
        session['actor_name'] = actor.name
        session['correct_movie_ids'] = movie_ids
        session['correct_movies'] = movies
        session['guessed_movies'] = []
        session['strikes'] = 0
        session['game_over'] = False
        actor.image_url = movie_service.get_actor_image_url(actor.name)
        session['actor_image_url'] =actor.image_url
        
        logger.info(f"Started new game with actor: {actor.name}")
        return jsonify({
            'actor_name': actor.name,
            'message': 'New game started!',
            'strikes': 0,
            'game_over': False,
            'actor_image_url': actor.image_url
        })
    
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    """Handle movie guess submission"""
    try:
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
        if movie_id in [str(m['id']) for m in guessed_movies]:
            return jsonify({'error': 'Movie already guessed'}), 400
        
        # Try to get movie from database first
        movie = db_service.get_movie_by_id(int(movie_id))
        if not movie:
            try:
                # Fall back to API if not in database
                movie_details = movie_service.get_movie_details(movie_id)
            except TMDBError as e:
                return jsonify({'error': str(e)}), 500
        else:
            movie_details = {
                'id': movie.tmdb_id,
                'title': movie.title,
                'release_date': f"{movie.release_year}-01-01",
                'revenue': movie.revenue,
                'poster_path': movie.poster_path
            }
        
        # Check if guess is correct
        is_correct = movie_id in session['correct_movie_ids']
        
        if is_correct:
            guessed_movies.append(movie_details)
            session['guessed_movies'] = guessed_movies
            
            # Calculate highest revenue
            highest_revenue = max([m['revenue'] for m in guessed_movies])
            
            # Check if all movies found
            if len(guessed_movies) == len(correct_movies):
                session['game_over'] = True
                return jsonify({
                    'correct': True,
                    'message': 'Congratulations! You found all movies!',
                    'game_over': True,
                    'guessed_movies': guessed_movies,
                    'strikes': session['strikes'],
                    'highest_revenue': highest_revenue
                })
            
            return jsonify({
                'correct': True,
                'message': 'Correct guess!',
                'guessed_movies': guessed_movies,
                'strikes': session['strikes'],
                'game_over': False,
                'highest_revenue': highest_revenue
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
                    'strikes': session['strikes'],
                    'highest_revenue': max([m['revenue'] for m in correct_movies])
                })
            
            return jsonify({
                'correct': False,
                'message': 'Incorrect guess!',
                'guessed_movies': guessed_movies,
                'strikes': session['strikes'],
                'game_over': False
            })
            
    except Exception as e:
        logger.error(f"Error in submit_guess: {str(e)}")
        return jsonify({'error': 'Server error processing guess'}), 500

@app.route('/search_movies')
def search_movies():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    try:
        # Try database search first
        movies = db_service.search_movies(query)
        
        # If no results, fallback to API
        if not movies:
            movies = movie_service.search_movies(query)
        
        return jsonify(movies)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/')
def home():
    if 'actor_name' not in session:
        start_game()
    
    # Calculate highest revenue from correct movies
    highest_revenue = max([m['revenue'] for m in session['correct_movies']] if session.get('correct_movies') else [0])
    
    return render_template('home.html', 
                         actor_name=session['actor_name'],
                         strikes=session['strikes'],
                         guessed_movies=session['guessed_movies'],
                         game_over=session['game_over'],
                         actor_image_url=session['actor_image_url'],
                         highest_revenue=highest_revenue
                         )

@app.route('/new_game')
def new_game():
    """Start a new game by clearing session and redirecting to home"""
    session.clear()  # Clear the current session
    return start_game()


if __name__ == '__main__':
    app.run(debug=True) 