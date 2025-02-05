from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from models import Base, Actor, Movie
from movie_data import MovieDataService
import os
from dotenv import load_dotenv
from typing import List, Dict
import time
from datetime import datetime

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost/movie_game')

# Initialize database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(engine)

def get_top_actors() -> List[Dict]:
    """Get list of top 100 actors from TMDB"""
    movie_service = MovieDataService()
    
    try:
        # Get popular actors from TMDB
        url = f"{movie_service.base_url}/person/popular"
        params = {"page": 1}
        actors = []
        
        # Fetch 5 pages to get top 100 actors
        for page in range(1, 6):
            params["page"] = page
            response = movie_service.make_request("GET", url, params=params)
            actors.extend(response.get("results", []))
            time.sleep(0.5)  # Rate limiting
        
        return sorted(actors, key=lambda x: x["popularity"], reverse=True)[:100]
    
    except Exception as e:
        print(f"Error fetching top actors: {e}")
        return []

def populate_actor_movies(session, movie_service: MovieDataService, actor_data: Dict):
    """Populate actor and their movies in database"""
    try:
        # Create actor record
        actor = Actor(
            tmdb_id=actor_data["id"],
            name=actor_data["name"],
            popularity=actor_data["popularity"]
        )
        
        # Get actor's movies
        movies = movie_service.get_actor_movies_with_details(actor_data["name"])
        
        for movie_data in movies:
            # Create movie if it doesn't exist
            movie = session.query(Movie).filter_by(tmdb_id=movie_data["id"]).first()
            if not movie:
                movie = Movie(
                    tmdb_id=movie_data["id"],
                    title=movie_data["title"],
                    release_year=int(movie_data["release_date"][:4]) if movie_data.get("release_date") else None,
                    revenue=movie_data.get("revenue"),
                    poster_path=movie_data.get("poster_path")
                )
            
            # Add movie to actor's movies with billing order
            actor.movies.append(movie)
        
        session.add(actor)
        session.commit()
        print(f"Added actor {actor.name} with {len(actor.movies)} movies")
        
    except Exception as e:
        session.rollback()
        print(f"Error adding actor {actor_data['name']}: {e}")

def main():
    """Main function to initialize database and populate data"""
    print("Creating database tables...")
    create_tables()
    
    movie_service = MovieDataService()
    session = SessionLocal()
    
    try:
        print("Fetching top actors...")
        top_actors = get_top_actors()
        
        print(f"Found {len(top_actors)} actors. Populating database...")
        for actor_data in top_actors:
            # Check if actor already exists
            existing = session.query(Actor).filter_by(tmdb_id=actor_data["id"]).first()
            if not existing:
                populate_actor_movies(session, movie_service, actor_data)
                time.sleep(1)  # Rate limiting
            else:
                print(f"Actor {actor_data['name']} already exists, skipping")
        
        print("Database population complete!")
        
    except Exception as e:
        print(f"Error during database population: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 