from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from models import Actor, Movie
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseService:
    def __init__(self):
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not set in environment")
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_db(self) -> Session:
        """Get database session"""
        db = self.SessionLocal()
        try:
            return db
        except Exception as e:
            db.close()
            raise e

    def get_random_actor(self) -> Optional[Actor]:
        """Get a random actor from the database"""
        with self.get_db() as db:
            try:
                # Get random actor with at least one movie
                actor = db.query(Actor)\
                         .filter(Actor.movies.any())\
                         .order_by(func.random())\
                         .first()
                if actor:
                    logger.info(f"Found random actor: {actor.name}")
                else:
                    logger.warning("No actors found in database")
                return actor
            except Exception as e:
                logger.error(f"Error getting random actor: {e}")
                raise

    def get_actor_movies(self, actor_name: str) -> List[Dict]:
        """Get actor's movies from database"""
        with self.get_db() as db:
            try:
                actor = db.query(Actor).filter(Actor.name == actor_name).first()
                if not actor:
                    logger.warning(f"Actor not found: {actor_name}")
                    return []
                
                # Convert to dictionary format expected by frontend
                movies = []
                for movie in sorted(actor.movies, key=lambda x: x.revenue or 0, reverse=True)[:5]:
                    movies.append({
                        'id': movie.tmdb_id,
                        'title': movie.title,
                        'release_date': f"{movie.release_year}-01-01" if movie.release_year else None,
                        'revenue': movie.revenue or 0
                    })
                
                logger.info(f"Found {len(movies)} movies for {actor_name}")
                return movies
            except Exception as e:
                logger.error(f"Error getting actor movies: {e}")
                raise

    def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        """Get movie by TMDB ID"""
        with self.get_db() as db:
            try:
                movie = db.query(Movie).filter(Movie.tmdb_id == movie_id).first()
                if movie:
                    logger.info(f"Found movie: {movie.title}")
                else:
                    logger.warning(f"Movie not found: {movie_id}")
                return movie
            except Exception as e:
                logger.error(f"Error getting movie by ID: {e}")
                raise

    def search_movies(self, query: str) -> List[Dict]:
        """Search movies in database"""
        with self.get_db() as db:
            try:
                movies = db.query(Movie)\
                          .filter(Movie.title.ilike(f"%{query}%"))\
                          .limit(10)\
                          .all()
                
                result = [{
                    'id': movie.tmdb_id,
                    'title': movie.title,
                    'year': str(movie.release_year) if movie.release_year else 'N/A'
                } for movie in movies]
                
                logger.info(f"Found {len(result)} movies matching '{query}'")
                return result
            except Exception as e:
                logger.error(f"Error searching movies: {e}")
                raise 