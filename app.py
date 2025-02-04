from flask import Flask, render_template

app = Flask(__name__)

# Mock data for movie suggestions
MOCK_MOVIES = [
    "Forrest Gump",
    "Cast Away",
    "Saving Private Ryan",
    "The Da Vinci Code",
    "Big"
]

@app.route('/')
def home():
    return render_template('home.html', actor_name="Tom Hanks", movies=MOCK_MOVIES)

@app.route('/new_game')
def new_game():
    # For now, just redirect to home with a fresh state
    return render_template('home.html', actor_name="Tom Hanks", movies=MOCK_MOVIES)

if __name__ == '__main__':
    app.run(debug=True) 