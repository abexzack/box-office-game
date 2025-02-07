#!/bin/bash

echo "Resetting database..."

# Clear connections, drop and recreate database, then initialize
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'movie_game' AND pid <> pg_backend_pid();" -c "DROP DATABASE IF EXISTS movie_game;" -c "CREATE DATABASE movie_game;" && python db_init.py

echo "Database reset complete!" 