# box-office-game

The game will be available at `http://localhost:5000`

## Features

- Focuses on established actors (15+ movies)
- Primarily includes actors from English-language films
- Updates trending actors weekly
- Tracks player progress and high scores
- Responsive design for mobile and desktop

## Database Filters

The actor database is filtered to include:
- Actors with at least 15 movie credits
- Actors who primarily work in English-language films (>70% of recent work)
- Most popular actors based on TMDB rankings

## Maintenance

The database is automatically updated weekly with:
- New trending actors
- Updated movie information
- Removal of outdated records (>1 year old)

## Initialize DB

The easiest way to reset the database is to use the reset script:
```bash
./reset_db.sh
```

Or manually run the commands:

# 1. First, terminate all connections
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'movie_game' AND pid <> pg_backend_pid();"

# 2. Then drop and recreate the database
sudo -u postgres psql -c "DROP DATABASE IF EXISTS movie_game;" -c "CREATE DATABASE movie_game;"

# 3. Finally, run db_init to populate
python db_init.py

## Run the game

python app.py

## Run the update

python update_trending.py

