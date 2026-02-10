from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Game, SessionLobby, UserProfile, SessionParticipant, CreditTransaction, SessionStatus
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

db.init_app(app)


# ============================================================================
# DATABASE INITIALIZATION - LOAD GAMES ON STARTUP
# ============================================================================
def load_games_from_json():
    """Load board games from hobbygames_full_export.json on app startup."""
    json_file = 'hobbygames_full_export.json'
    
    if not os.path.exists(json_file):
        return
    
    with app.app_context():
        try:
            # Check if games already loaded
            if Game.query.first() is not None:
                return
            
            # Load JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                games_data = json.load(f)
            
            print(f"📖 Loading {len(games_data)} games from {json_file}...")
            
            added_count = 0
            for game_data in games_data:
                try:
                    title = game_data.get('title', 'Unknown Game')
                    price = game_data.get('price', 'N/A')
                    image_url = None
                    
                    # Get first image from gallery
                    gallery = game_data.get('gallery', [])
                    if gallery and len(gallery) > 0:
                        image_url = gallery[0]
                    
                    game = Game(
                        title=title,
                        price=price,
                        image_url=image_url,
                        is_available=True,
                        full_data=game_data
                    )
                    
                    db.session.add(game)
                    added_count += 1
                    
                    # Commit in batches
                    if added_count % 50 == 0:
                        db.session.commit()
                
                except Exception as e:
                    db.session.rollback()
                    continue
            
            db.session.commit()
            print(f"✅ Loaded {added_count} games into database")
        
        except Exception as e:
            print(f"⚠️  Could not load games: {str(e)}")


# ============================================================================
# UTILITIES & DECORATORS
# ============================================================================
def get_current_user():
    """Get the current user from session (simplified - use proper auth in production)."""
    user_id = request.args.get('user_id') or request.form.get('user_id')
    if user_id:
        return UserProfile.query.get(int(user_id))
    return None


def require_user(f):
    """Decorator to require an authenticated user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
        return f(user=user, *args, **kwargs)
    return decorated_function


# ============================================================================
# AUTHENTICATION & USER PROFILES
# ============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login page (simplified - use proper OAuth/JWT in production)."""
    if request.method == 'POST':
        username = request.form.get('username')
        
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return redirect(url_for('login'))
        
        user = UserProfile.query.filter_by(username=username).first()
        
        if not user:
            # Auto-create user if doesn't exist (simplified flow)
            try:
                user = UserProfile(username=username)
                db.session.add(user)
                db.session.commit()
                flash(f'Welcome {username}!', 'success')
            except Exception as e:
                flash(f'Error creating user: {str(e)}', 'error')
                return redirect(url_for('login'))
        
        # Redirect to dashboard with user_id
        return redirect(url_for('dashboard', user_id=user.id))
    
    return render_template('login.html')


@app.route('/profile/<int:user_id>')
def profile(user_id):
    """View user profile and credit history."""
    user = UserProfile.query.get_or_404(user_id)
    transactions = CreditTransaction.query.filter_by(user_id=user_id).order_by(
        CreditTransaction.created_at.desc()
    ).limit(20).all()
    
    recent_sessions = SessionParticipant.query.filter_by(user_id=user_id).all()
    
    return render_template(
        'profile.html', 
        user=user, 
        transactions=transactions,
        recent_sessions=recent_sessions
    )


# ============================================================================
# DASHBOARD & MAIN VIEWS
# ============================================================================
@app.route('/')
def index():
    """Redirect to login if no user, else to dashboard."""
    user_id = request.args.get('user_id')
    if user_id:
        return redirect(url_for('dashboard', user_id=user_id))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard showing cafe floor status."""
    user = get_current_user()
    
    try:
        active_sessions = SessionLobby.query.filter_by(
            status=SessionStatus.ACTIVE.value
        ).all()
        recruiting_sessions = SessionLobby.query.filter_by(
            status=SessionStatus.RECRUITING.value
        ).all()
        
        # Provide a harmless example row if there are no sessions to show
        example_sessions = []
        if not recruiting_sessions and not active_sessions:
            example_sessions = [{
                'game_name': 'Example: Catan',
                'slots_remaining': 3,
                'slots_total': 4,
                'status': SessionStatus.RECRUITING.value
            }]
        
        # Get stats for the current user
        user_stats = None
        if user:
            user_stats = {
                'sessions_completed': user.sessions_completed,
                'reliability_streak': user.reliability_streak,
                'credit_balance': user.credit_balance,
                'can_join': user.can_join_session()
            }
        
        return render_template(
            'dashboard.html',
            active=active_sessions,
            recruiting=recruiting_sessions,
            example_sessions=example_sessions,
            user=user,
            user_stats=user_stats
        )
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', active=[], recruiting=[], example_sessions=[], user=user)


@app.route('/library')
def library():
    """Staff view of the physical game shelf."""
    try:
        games = Game.query.all()
        return render_template('library.html', games=games)
    except Exception as e:
        flash(f'Error loading library: {str(e)}', 'error')
        return render_template('library.html', games=[])


@app.route('/game/<int:game_id>')
def game_details(game_id):
    """Detailed view of a single game."""
    try:
        game = Game.query.get_or_404(game_id)
        user_id = request.args.get('user_id')
        
        # Get active sessions for this game
        active_lobbies = SessionLobby.query.filter_by(
            game_id=game_id,
            status=SessionStatus.RECRUITING.value
        ).all()
        
        return render_template('game_details.html', game=game, lobbies=active_lobbies, user_id=user_id)
    except Exception as e:
        flash(f'Error loading game details: {str(e)}', 'error')
        user_id = request.args.get('user_id')
        return redirect(url_for('library', user_id=user_id))


# ============================================================================
# STAFF CONTROLS - Shelf Management
# ============================================================================
@app.route('/toggle_game/<int:game_id>', methods=['POST'])
def toggle_game(game_id):
    """Toggle game availability status (staff only)."""
    try:
        game = Game.query.get_or_404(game_id)
        game.is_available = not game.is_available
        db.session.commit()
        
        flash(f'Game "{game.title}" availability updated', 'success')
        return redirect(url_for('library'))
    except Exception as e:
        flash(f'Error updating game: {str(e)}', 'error')
        return redirect(url_for('library'))


# ============================================================================
# LFG SESSION MANAGEMENT
# ============================================================================
@app.route('/session/create', methods=['GET', 'POST'])
@require_user
def create_session(user):
    """Create a new LFG session."""
    try:
        if request.method == 'POST':
            game_id = request.form.get('game_id', type=int)
            slots_total = request.form.get('slots_total', type=int, default=4)
            
            # Validation
            user_id = request.form.get('user_id')
            if not game_id or not Game.query.get(game_id):
                flash('Invalid game selected', 'error')
                games = Game.query.all()  # Show all games on error
                return render_template('create_session.html', games=games, user_id=user_id)
            
            if slots_total < 2 or slots_total > 10:
                flash('Players must be between 2 and 10', 'error')
                games = Game.query.all()  # Show all games on error
                return render_template('create_session.html', games=games, user_id=user_id)
            
            # Create session with current user as host
            session = SessionLobby(
                game_id=game_id,
                slots_total=slots_total,
                slots_filled=1,  # Host counts as 1 player
                status=SessionStatus.RECRUITING.value,
                host_id=user.id
            )
            db.session.add(session)
            db.session.flush()  # Get session.id without committing
            
            # Add host as first participant
            participant = SessionParticipant(session_id=session.id, user_id=user.id)
            session.participants.append(participant)
            
            db.session.commit()
            
            flash(f'Session created for {Game.query.get(game_id).title}!', 'success')
            return redirect(url_for('view_session', session_id=session.id) + f'?user_id={user.id}')
        
        # GET request - show available games first, fall back to all if none available
        games = Game.query.filter_by(is_available=True).all()
        if not games:
            games = Game.query.all()
        user_id = request.args.get('user_id')
        return render_template('create_session.html', games=games, user=user, user_id=user_id)
    
    except Exception as e:
        flash(f'Error creating session: {str(e)}', 'error')
        return redirect(url_for('dashboard') + f'?user_id={user.id}')


@app.route('/session/<int:session_id>')
def view_session(session_id):
    """View details of a specific session."""
    try:
        user = get_current_user()
        session = SessionLobby.query.get_or_404(session_id)
        user_id = request.args.get('user_id')
        
        return render_template('view_session.html', session=session, user=user, user_id=user_id)
    except Exception as e:
        flash(f'Error loading session: {str(e)}', 'error')
        user_id = request.args.get('user_id')
        if user_id:
            return redirect(url_for('dashboard', user_id=user_id))
        return redirect(url_for('login'))


@app.route('/session/<int:session_id>/join', methods=['POST'])
@require_user
def join_session(session_id, user):
    """Join an existing session."""
    try:
        session = SessionLobby.query.get_or_404(session_id)
        
        # Validation
        if session.status != SessionStatus.RECRUITING.value:
            flash('This session is not recruiting', 'error')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        if session.is_full:
            flash('Session is full', 'error')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        # Check if user already in session
        if any(p.user_id == user.id for p in session.participants):
            flash('You are already in this session', 'warning')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        # Add participant
        session.add_participant(user)
        db.session.commit()
        
        flash(f'Joined session! {session.slots_remaining} slot(s) remaining', 'success')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
    
    except ValueError as e:
        flash(f'Cannot join: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
    except Exception as e:
        flash(f'Error joining session: {str(e)}', 'error')
        return redirect(url_for('dashboard') + f'?user_id={user.id}')


@app.route('/session/<int:session_id>/leave', methods=['POST'])
@require_user
def leave_session(session_id, user):
    """Leave a session."""
    try:
        session = SessionLobby.query.get_or_404(session_id)
        
        # Cannot leave if hosting
        if session.host_id == user.id:
            flash('Hosts cannot leave their own session. Cancel it instead.', 'warning')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        session.remove_participant(user)
        db.session.commit()
        
        flash('Left session', 'success')
        return redirect(url_for('dashboard') + f'?user_id={user.id}')
    
    except Exception as e:
        flash(f'Error leaving session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')


@app.route('/session/<int:session_id>/start', methods=['POST'])
@require_user
def start_session(session_id, user):
    """Start an active session (host only)."""
    try:
        session = SessionLobby.query.get_or_404(session_id)
        
        # Validation
        if session.host_id != user.id:
            flash('Only the host can start the session', 'error')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        if not session.can_start:
            flash(f'Need at least 2 players. Currently {session.slots_filled}', 'error')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        session.status = SessionStatus.ACTIVE.value
        session.started_at = datetime.utcnow()
        db.session.commit()
        
        flash('Session started! Have fun!', 'success')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
    
    except Exception as e:
        flash(f'Error starting session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')


@app.route('/session/<int:session_id>/complete', methods=['POST'])
@require_user
def complete_session(session_id, user):
    """Complete a session and award credits (host only)."""
    try:
        session = SessionLobby.query.get_or_404(session_id)
        
        # Validation
        if session.host_id != user.id:
            flash('Only the host can complete the session', 'error')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        session.complete_session()
        db.session.commit()
        
        flash('Session completed! Credits awarded to all participants.', 'success')
        return redirect(url_for('dashboard') + f'?user_id={user.id}')
    
    except ValueError as e:
        flash(f'Cannot complete: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
    except Exception as e:
        flash(f'Error completing session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')


@app.route('/session/<int:session_id>/cancel', methods=['POST'])
@require_user
def cancel_session(session_id, user):
    """Cancel a session (host only)."""
    try:
        session = SessionLobby.query.get_or_404(session_id)
        
        # Validation
        if session.host_id != user.id:
            flash('Only the host can cancel the session', 'error')
            return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')
        
        session.status = SessionStatus.CANCELLED.value
        
        # Penalize host for cancellation
        user.reliability_streak = max(0, user.reliability_streak - 2)
        transaction = CreditTransaction(
            user_id=user.id,
            amount=-5,
            transaction_type='SESSION_CANCELLED',
            description=f'Session #{session_id} cancelled by host'
        )
        user.credit_balance -= 5
        db.session.add(transaction)
        db.session.commit()
        
        flash('Session cancelled. Penalty applied.', 'warning')
        return redirect(url_for('dashboard') + f'?user_id={user.id}')
    
    except Exception as e:
        flash(f'Error cancelling session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id) + f'?user_id={user.id}')


# ============================================================================
# CREDIT SYSTEM
# ============================================================================
@app.route('/credits')
def credits():
    """View credits/economy info."""
    user = get_current_user()
    
    if not user:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    transactions = CreditTransaction.query.filter_by(user_id=user.id).order_by(
        CreditTransaction.created_at.desc()
    ).limit(50).all()
    
    return render_template('credits.html', user=user, transactions=transactions)


# ============================================================================
# API ENDPOINTS (for AJAX requests)
# ============================================================================
@app.route('/api/sessions')
def api_sessions():
    """Get all recruiting sessions as JSON."""
    try:
        sessions = SessionLobby.query.filter_by(
            status=SessionStatus.RECRUITING.value
        ).all()
        
        data = [{
            'id': s.id,
            'game': s.game.title,
            'host': s.host.username,
            'slots_filled': s.slots_filled,
            'slots_total': s.slots_total,
            'created_at': s.created_at.isoformat()
        } for s in sessions]
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    """Get user info as JSON."""
    try:
        user = UserProfile.query.get_or_404(user_id)
        return jsonify({
            'id': user.id,
            'username': user.username,
            'credit_balance': user.credit_balance,
            'reliability_streak': user.reliability_streak,
            'sessions_completed': user.sessions_completed,
            'can_join': user.can_join_session()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', error='Page not found', code=404), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    db.session.rollback()
    return render_template('error.html', error='Internal server error', code=500), 500


@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors."""
    return render_template('error.html', error='Access forbidden', code=403), 403


# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================
@app.context_processor
def inject_user():
    """Make current user available in all templates."""
    return {'current_user': get_current_user()}


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_games_from_json()
    app.run(debug=True, host='0.0.0.0', port=5000)