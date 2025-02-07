from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import Actor, Movie, Base
from movie_data import MovieDataService
from datetime import datetime, timedelta
from typing import List, Dict
import logging
from dotenv import load_dotenv
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseUpdater:
    def __init__(self):
        self.engine = create_engine(os.getenv('DATABASE_URL'))
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.movie_service = MovieDataService()
        
    def get_trending_actors(self) -> List[Dict]:
        """Fetch trending actors from TMDB"""
        try:
            url = f"{self.movie_service.base_url}/trending/person/week"
            response = self.movie_service.make_request("GET", url)
            
            actors = []
            for person in response.get("results", []):
                if person.get("known_for_department") != "Acting":
                    continue
                    
                # Get their movie credits first to check total count
                movie_credits = self.movie_service.make_request(
                    "GET",
                    f"{self.movie_service.base_url}/person/{person['id']}/movie_credits"
                )
                
                all_movies = movie_credits.get("cast", [])
                # Skip if they don't have at least 15 movies
                if len(all_movies) < 15:
                    logger.info(f"Skipping {person['name']}: Only {len(all_movies)} movies")
                    continue
                
                # Check their known_for movies
                known_for = person.get("known_for", [])
                english_language_films = [
                    movie for movie in known_for 
                    if movie.get("original_language") == "en" and movie.get("media_type") == "movie"
                ]
                
                # Only include actors with majority English language films
                if len(english_language_films) >= len(known_for) * 0.5:
                    actors.append(person)
            
            logger.info(f"Found {len(actors)} trending English-language film actors with 15+ movies")
            return actors
        except Exception as e:
            logger.error(f"Error fetching trending actors: {e}")
            return []

    def update_actor_movies(self, actor_data: Dict) -> None:
        """Update or create actor and their movies"""
        with self.SessionLocal() as session:
            try:
                # Check if actor exists
                actor = session.query(Actor).filter_by(tmdb_id=actor_data["id"]).first()
                
                if not actor:
                    # Get more detailed actor info including place of birth
                    actor_details = self.movie_service.make_request(
                        "GET", 
                        f"{self.movie_service.base_url}/person/{actor_data['id']}"
                    )
                    
                    # Skip if we can't verify they work primarily in English-language films
                    movie_credits = self.movie_service.make_request(
                        "GET",
                        f"{self.movie_service.base_url}/person/{actor_data['id']}/movie_credits"
                    )
                    
                    all_movies = movie_credits.get("cast", [])
                    if all_movies:
                        # Get language details for their movies
                        english_movies = 0
                        total_movies = 0
                        for movie in all_movies[:20]:  # Check their 20 most recent movies
                            movie_details = self.movie_service.make_request(
                                "GET",
                                f"{self.movie_service.base_url}/movie/{movie['id']}"
                            )
                            if movie_details.get("original_language") == "en":
                                english_movies += 1
                            total_movies += 1
                        
                        # Skip if less than 70% of their recent work is in English
                        if total_movies > 0 and (english_movies / total_movies) < 0.7:
                            logger.info(f"Skipping {actor_data['name']}: Insufficient English language films")
                            return
                    
                    actor = Actor(
                        tmdb_id=actor_data["id"],
                        name=actor_data["name"],
                        popularity=actor_data["popularity"]
                    )
                    session.add(actor)
                else:
                    actor.popularity = actor_data["popularity"]
                
                # Update last_updated timestamp
                actor.last_updated = datetime.utcnow()
                
                # Get actor's movies
                movies = self.movie_service.get_actor_movies_with_details(actor.name)
                
                # Update movies
                for movie_data in movies:
                    movie = session.query(Movie).filter_by(tmdb_id=movie_data["id"]).first()
                    
                    if not movie:
                        movie = Movie(
                            tmdb_id=movie_data["id"],
                            title=movie_data["title"],
                            release_year=int(movie_data["release_date"][:4]) if movie_data.get("release_date") else None,
                            revenue=movie_data.get("revenue"),
                            poster_path=movie_data.get("poster_path")
                        )
                        session.add(movie)
                    
                    # Ensure movie is associated with actor
                    if movie not in actor.movies:
                        actor.movies.append(movie)
                
                session.commit()
                logger.info(f"Updated actor {actor.name} with {len(movies)} movies")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error updating actor {actor_data['name']}: {e}")

    def remove_outdated_records(self) -> None:
        """Remove actors not updated in over a year"""
        with self.SessionLocal() as session:
            try:
                one_year_ago = datetime.utcnow() - timedelta(days=365)
                outdated_actors = session.query(Actor).filter(
                    Actor.last_updated < one_year_ago
                ).all()
                
                for actor in outdated_actors:
                    session.delete(actor)
                
                session.commit()
                logger.info(f"Removed {len(outdated_actors)} outdated actors")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error removing outdated records: {e}")

    def update_database(self) -> None:
        """Main update function"""
        logger.info("Starting database update")
        
        try:
            # Get trending actors
            trending_actors = self.get_trending_actors()
            
            # Update each actor
            for actor_data in trending_actors:
                self.update_actor_movies(actor_data)
            
            # Clean up old records
            self.remove_outdated_records()
            
            logger.info("Database update completed successfully")
            
        except Exception as e:
            logger.error(f"Error during database update: {e}")

def run_update():
    """Function to be called by scheduler"""
    updater = DatabaseUpdater()
    updater.update_database()

def main():
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Schedule update to run every Monday at 3 AM
    scheduler.add_job(
        run_update,
        trigger=CronTrigger(day_of_week='mon', hour=3),
        id='update_trending_actors',
        name='Weekly trending actors update'
    )
    
    # Run initial update
    run_update()
    
    # Start scheduler
    logger.info("Starting scheduler")
    scheduler.start()

if __name__ == "__main__":
    main() 