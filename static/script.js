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
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        // Clear search
        document.getElementById('movie-search').value = '';
        document.getElementById('search-results').innerHTML = '';

        // Refresh page if game is over
        if (data.game_over) {
            location.reload();
            return;
        }

        // Update UI
        updateGameState(data);
    });
}

function updateGameState(data) {
    // Update strikes with animation
    const strikes = document.querySelectorAll('.strike');
    strikes.forEach((strike, index) => {
        if (index < data.strikes) {
            strike.classList.add('active');
        }
    });

    // Refresh the page to update guessed movies
    // In a more advanced version, you could update the DOM directly
    location.reload();
} 