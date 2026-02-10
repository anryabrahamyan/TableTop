from flask import Flask, render_template, request, redirect, url_for
from models import db, Game, SessionLobby

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/tabletop_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def dashboard():
    # Fetch active sessions and table status for the dashboard
    active_sessions = SessionLobby.query.filter_by(status='ACTIVE').all()
    recruiting_sessions = SessionLobby.query.filter_by(status='RECRUITING').all()
    return render_template('dashboard.html', active=active_sessions, recruiting=recruiting_sessions)

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
    app.run(debug=True)