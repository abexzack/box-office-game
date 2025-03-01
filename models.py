from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, BigInteger, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

Base = declarative_base()

# Association table for actor-movie many-to-many relationship
actor_movies = Table(
    'actor_movies',
    Base.metadata,
    Column('actor_id', Integer, ForeignKey('actors.tmdb_id')),
    Column('movie_id', Integer, ForeignKey('movies.tmdb_id')),
    Column('order', Integer),  # Actor's billing order in the movie
)

class Actor(Base):
    __tablename__ = 'actors'

    tmdb_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    popularity = Column(Integer)  # TMDB popularity score
    last_updated = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    movies = relationship(
        'Movie',
        secondary=actor_movies,
        back_populates='actors'
    )

class Movie(Base):
    __tablename__ = 'movies'

    tmdb_id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    release_year = Column(Integer)
    revenue = Column(BigInteger)
    poster_path = Column(String(255))
    
    actors = relationship(
        'Actor',
        secondary=actor_movies,
        back_populates='movies'
    ) 