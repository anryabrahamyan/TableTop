from flask import Flask, render_template, request, redirect, url_for
from models import db, Game, SessionLobby
import os
from dotenv import load_dotenv

load_dotenv() # This loads the variables from the .env file
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def dashboard():
    # FR.2.1: Filter lobbies by state for better floor awareness
    recruiting_lobbies = SessionLobby.query.filter_by(status='RECRUITING').all()
    active_sessions = SessionLobby.query.filter_by(status='ACTIVE').all()
    
    # FR.4.1: Pull admin profile for the Credit Ledger view
    user = UserProfile.query.first() 
    
    return render_template('dashboard.html', 
                           recruiting=recruiting_lobbies, 
                           active=active_sessions, 
                           user=user)
@app.route('/library')
def library():
    # Staff view of the physical game shelf
    games = Game.query.all()
    return render_template('library.html', games=games)

@app.route('/toggle_game/<int:game_id>')
def toggle_game(game_id):
    # Functional Req: Shelf-to-App Sync
    game = Game.query.get(game_id)
    game.is_available = not game.is_available
    db.session.commit()
    return redirect(url_for('library'))

@app.route('/game/<int:game_id>')
def game_details(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('game_details.html', game=game)

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5000)