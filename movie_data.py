from tmdbv3api import TMDb, Person, Movie
from typing import List, Optional, Dict
import time
from functools import lru_cache
import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

class TMDBError(Exception):
    """Custom exception for TMDB API errors"""
    pass

class MovieDataService:
    def __init__(self, access_token: Optional[str] = None):
        self.tmdb = TMDb()
        self.access_token = access_token or os.getenv('TMDB_TOKEN')
        if not self.access_token:
            raise ValueError("TMDB access token is required. Set TMDB_TOKEN in .env file or pass to constructor.")
        
        # Set up headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json;charset=utf-8"
        }
        
        self.base_url = "https://api.themoviedb.org/3"
        self.cache_timeout = 3600  # 1 hour

    @lru_cache(maxsize=100)
    def get_actor_movies(self, actor_name: str) -> List[str]:
        """
        Get the top 5 highest-grossing movies for an actor.
        
        Args:
            actor_name (str): The name of the actor to search for
            
        Returns:
            List[str]: List of movie titles
            
        Raises:
            TMDBError: If there's an error with the API or actor not found
        """
        try:
            # Search for the actor
            search_url = f"{self.base_url}/search/person"
            params = {"query": actor_name}
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            results = response.json().get("results", [])
            if not results:
                raise TMDBError(f"No results found for actor: {actor_name}")
            
            actor_id = results[0]["id"]
            
            # Get actor's movie credits
            credits_url = f"{self.base_url}/person/{actor_id}/movie_credits"
            response = requests.get(credits_url, headers=self.headers)
            response.raise_for_status()
            
            movie_credits = response.json().get("cast", [])
            
            # Filter and process movies
            valid_movies = []
            for credit in movie_credits:
                if credit.get("order", 999) <= 3:  # Only include movies where actor had a major role
                    # Get full movie details
                    movie_url = f"{self.base_url}/movie/{credit['id']}"
                    response = requests.get(movie_url, headers=self.headers)
                    if response.status_code == 200:
                        movie_details = response.json()
                        if movie_details.get("revenue", 0) > 0:
                            valid_movies.append({
                                "title": movie_details["title"],
                                "revenue": movie_details["revenue"]
                            })
            
            # Sort by revenue and get top 5
            valid_movies.sort(key=lambda x: x["revenue"], reverse=True)
            top_movies = valid_movies[:5]
            
            return [movie["title"] for movie in top_movies]
            
        except requests.exceptions.RequestException as e:
            raise TMDBError(f"Error fetching actor movies: {str(e)}")

    def clear_cache(self):
        """Clear the cached results"""
        self.get_actor_movies.cache_clear()

    def search_movies(self, query: str) -> List[dict]:
        """
        Search for movies using TMDB API.
        
        Args:
            query (str): Search query string
            
        Returns:
            List[dict]: List of movies with title and year
        """
        try:
            search_url = f"{self.base_url}/search/movie"
            params = {
                "query": query,
                "include_adult": False,
                "page": 1
            }
            
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            results = response.json().get("results", [])
            
            # Format and limit results
            movies = []
            for movie in results[:10]:  # Limit to 10 results
                if movie.get("release_date"):
                    year = movie["release_date"][:4]
                else:
                    year = "N/A"
                    
                movies.append({
                    "id": movie["id"],
                    "title": movie["title"],
                    "year": year
                })
                
            return movies
            
        except requests.exceptions.RequestException as e:
            raise TMDBError(f"Error searching movies: {str(e)}")

    def get_actor_movies_with_details(self, actor_name: str) -> List[Dict]:
        """Get actor's movies with full details"""
        try:
            # Search for the actor
            search_url = f"{self.base_url}/search/person"
            params = {"query": actor_name}
            response = requests.get(search_url, headers=self.headers, params=params)
            response.raise_for_status()
            
            results = response.json().get("results", [])
            if not results:
                raise TMDBError(f"No results found for actor: {actor_name}")
            
            actor_id = results[0]["id"]
            
            # Get actor's movie credits
            credits_url = f"{self.base_url}/person/{actor_id}/movie_credits"
            response = requests.get(credits_url, headers=self.headers)
            response.raise_for_status()
            
            movie_credits = response.json().get("cast", [])
            
            # Filter and process movies
            valid_movies = []
            for credit in movie_credits:
                # Relaxed criteria: include movies where actor is in top 10 billing
                if credit.get("order", 999) <= 10:  
                    try:
                        movie_details = self.get_movie_details(credit['id'])
                        # Include movies with any revenue data and released in theaters
                        if (movie_details and 
                            movie_details.get("release_date") and  # Has release date
                            movie_details.get("revenue", 0) >= 0 and  # Has any revenue (including 0)
                            movie_details.get("release_type", "") != "TV"  # Not a TV movie
                        ):
                            valid_movies.append(movie_details)
                    except Exception as e:
                        print(f"Error fetching details for movie {credit['id']}: {e}")
                        continue
            
            # Sort by revenue and get top 5
            valid_movies.sort(key=lambda x: x.get("revenue", 0), reverse=True)
            return valid_movies[:5]
            
        except requests.exceptions.RequestException as e:
            raise TMDBError(f"Error fetching actor movies: {str(e)}")

    def get_movie_details(self, movie_id: str) -> Dict:
        """Get full movie details by ID"""
        try:
            movie_url = f"{self.base_url}/movie/{movie_id}"
            response = requests.get(movie_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise TMDBError(f"Error fetching movie details: {str(e)}")

    def make_request(self, method: str, url: str, params: dict = None) -> dict:
        """
        Make a request to TMDB API
        
        Args:
            method (str): HTTP method (GET, POST, etc.)
            url (str): API endpoint URL
            params (dict, optional): Query parameters
            
        Returns:
            dict: JSON response from API
            
        Raises:
            TMDBError: If request fails
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise TMDBError(f"API request failed: {str(e)}") 