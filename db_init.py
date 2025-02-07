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
import logging

# At the top of the file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
        url = f"{movie_service.base_url}/person/popular"
        params = {"page": 1}
        all_actors = []
        
        logging.info("Starting to fetch actors from TMDB...")
        
        # Fetch 10 pages to get enough actors (we'll filter many out)
        for page in range(1, 11):
            logging.info(f"Fetching page {page} of actors...")
            params["page"] = page
            response = movie_service.make_request("GET", url, params=params)
            
            for person in response.get("results", []):
                if person.get("known_for_department") != "Acting":
                    continue
                
                logging.info(f"Checking actor: {person.get('name', 'Unknown')}")
                
                # Get their movie credits first to check total count
                movie_credits = movie_service.make_request(
                    "GET",
                    f"{movie_service.base_url}/person/{person['id']}/movie_credits"
                )
                
                all_movies = movie_credits.get("cast", [])
                # Skip if they don't have at least 15 movies
                if len(all_movies) < 15:
                    logging.info(f"Skipping {person['name']}: Only {len(all_movies)} movies")
                    continue
                
                # Check their known_for movies
                known_for = person.get("known_for", [])
                english_language_films = [
                    movie for movie in known_for 
                    if movie.get("original_language") == "en" and movie.get("media_type") == "movie"
                ]
                
                # Only include actors with majority English language films
                if len(english_language_films) >= len(known_for) * 0.5:
                    # Check language of their recent movies
                    english_movies = 0
                    total_movies = 0
                    logging.info(f"Checking recent movies for {person['name']}...")
                    
                    for movie in all_movies[:20]:
                        movie_details = movie_service.make_request(
                            "GET",
                            f"{movie_service.base_url}/movie/{movie['id']}"
                        )
                        if movie_details.get("original_language") == "en":
                            english_movies += 1
                        total_movies += 1
                        time.sleep(0.25)  # Add small delay between movie requests
                    
                    # Only include if 70% or more of their recent work is in English
                    if total_movies > 0 and (english_movies / total_movies) >= 0.7:
                        all_actors.append(person)
                        logging.info(f"Added actor: {person['name']} ({len(all_movies)} movies)")
            
            time.sleep(1)  # Increased delay between pages
            
            # Break if we have enough actors
            if len(all_actors) >= 100:
                logging.info("Reached 100 actors, stopping search")
                break
        
        logging.info(f"Found total of {len(all_actors)} qualifying actors")
        return sorted(all_actors, key=lambda x: x["popularity"], reverse=True)[:100]
    
    except Exception as e:
        logging.error(f"Error fetching top actors: {e}")
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
        logging.info(f"Added actor {actor.name} with {len(actor.movies)} movies")
        
    except Exception as e:
        session.rollback()
        logging.error(f"Error adding actor {actor_data['name']}: {e}")

def main():
    """Main function to initialize database and populate data"""
    logging.info("Starting database initialization...")
    
    try:
        logging.info("Creating database tables...")
        create_tables()
        
        movie_service = MovieDataService()
        session = SessionLocal()
        
        logging.info("Fetching top actors from TMDB...")
        top_actors = get_top_actors()
        logging.info(f"Retrieved {len(top_actors)} actors from TMDB")
        
        if not top_actors:
            logging.error("No actors were retrieved from TMDB!")
            return
        
        logging.info("Starting database population...")
        for i, actor_data in enumerate(top_actors, 1):
            try:
                # Check if actor already exists
                existing = session.query(Actor).filter_by(tmdb_id=actor_data["id"]).first()
                if not existing:
                    logging.info(f"[{i}/{len(top_actors)}] Adding {actor_data['name']}...")
                    populate_actor_movies(session, movie_service, actor_data)
                    time.sleep(0.5)  # Rate limiting
                else:
                    logging.info(f"[{i}/{len(top_actors)}] Actor {actor_data['name']} already exists")
            except Exception as e:
                logging.error(f"Error processing actor {actor_data.get('name', 'unknown')}: {e}")
                continue
        
        session.commit()
        logging.info("Database population complete!")
        
    except Exception as e:
        logging.error(f"Error during database initialization: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # Set logging to show everything
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main() 