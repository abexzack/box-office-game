document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('movie-search');
    const searchResults = document.getElementById('search-results');
    let searchTimeout;

    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.innerHTML = '';
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/search_movies?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(movies => {
                    searchResults.innerHTML = movies.map(movie => `
                        <div class="search-result" onclick="submitGuess(${movie.id})">
                            ${movie.title} (${movie.year})
                        </div>
                    `).join('');
                });
        }, 300);
    });

    // Close search results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchResults.contains(e.target) && e.target !== searchInput) {
            searchResults.innerHTML = '';
        }
    });
});

function submitGuess(movieId) {
    fetch('/submit_guess', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ movie_id: movieId })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        // Clear search
        document.getElementById('movie-search').value = '';
        document.getElementById('search-results').innerHTML = '';

        if (data.error) {
            showMessage(data.error, 'error');
            return;
        }

        // Update UI
        updateGameState(data);
        showMessage(data.message, data.correct ? 'success' : 'error');
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage(error.error || 'Error submitting guess', 'error');
    });
}

function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = `message ${type} show`;
    setTimeout(() => {
        messageDiv.classList.remove('show');
    }, 3000);
}

function updateGameState(data) {
    // Update strikes with animation
    const strikes = document.querySelectorAll('.strike');
    strikes.forEach((strike, index) => {
        if (index < data.strikes) {
            strike.classList.add('active');
        }
    });

    if (data.correct) {
        // Add the new movie to the display without refreshing
        const guessedMoviesContainer = document.querySelector('.guessed-movies');
        const movieCard = document.createElement('div');
        movieCard.className = 'movie-card';
        
        const latestMovie = data.guessed_movies[data.guessed_movies.length - 1];
        movieCard.innerHTML = `
            <img class="movie-poster" 
                 src="${latestMovie.poster_path ? 
                      'https://image.tmdb.org/t/p/w200' + latestMovie.poster_path : 
                      '/static/placeholder.png'}" 
                 alt="${latestMovie.title}">
            <div class="movie-info">
                <div class="movie-title">${latestMovie.title}</div>
                <div class="movie-year">${latestMovie.release_date.slice(0,4)}</div>
                <div class="revenue-bar-container">
                    <div class="revenue-bar" style="width: ${(latestMovie.revenue / data.highest_revenue * 100)}%"></div>
                </div>
                <div class="revenue-text">$${(latestMovie.revenue / 1000000).toFixed(0)}M</div>
            </div>
        `;
        
        guessedMoviesContainer.appendChild(movieCard);
    }

    // Only refresh if game is over
    if (data.game_over) {
        location.reload();
    }
} 