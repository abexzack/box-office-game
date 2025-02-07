from db_service import DatabaseService
from models import Actor, Movie
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    db = DatabaseService()
    
    try:
        with db.get_db() as session:
            # Check total counts
            actor_count = session.query(Actor).count()
            movie_count = session.query(Movie).count()
            
            logger.info(f"Database contains {actor_count} actors and {movie_count} movies")
            
            # Check actors with movies
            actors_with_movies = session.query(Actor).filter(Actor.movies.any()).count()
            logger.info(f"Actors with at least one movie: {actors_with_movies}")
            
            # Show sample of actors and their movies
            logger.info("\nSample of actors in database:")
            actors = session.query(Actor).limit(5).all()
            for actor in actors:
                logger.info(f"Actor: {actor.name}")
                logger.info(f"- Movies: {len(actor.movies)}")
                for movie in actor.movies[:3]:  # Show first 3 movies
                    logger.info(f"  - {movie.title} ({movie.release_year})")
                logger.info("")
                
    except Exception as e:
        logger.error(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database() 