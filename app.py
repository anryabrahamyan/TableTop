from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, Game, SessionLobby, UserProfile, SessionParticipant, CreditTransaction, SessionStatus, VenueConfig
import os
import json
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///tabletop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

db.init_app(app)


def load_games_from_json():
    """Load board games from hobbygames_full_export.json on app startup."""
    json_file = 'hobbygames_full_export.json'
    
    if not os.path.exists(json_file):
        return

    with app.app_context():
        # ... logic ... (abbreviated for tool call, will use multi_replace if needed but this is a large chunk replacement structure)
        pass # The previous load_games_from_json logic is fine, I will just call run_migrations() in the main block or before it.

# Actually, I'll add the run_migrations function and call it in the main block, then update login and create_session separately.
# Let's do this in separate chunks for safety.


    """Load board games from hobbygames_full_export.json on app startup."""
    json_file = 'hobbygames_full_export.json'
    
    if not os.path.exists(json_file):
        return

    with app.app_context():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                games_data = json.load(f)
            
            if not isinstance(games_data, list):
                return

            print(f"📖 Checking {len(games_data)} games from {json_file}...")
            
            # Get existing game titles
            existing_titles = {title for (title,) in db.session.query(Game.title).all()}
            
            added_count = 0
            for game_data in games_data:
                try:
                    title = str(game_data.get('title', 'Unknown Game')).strip()
                    
                    if not title or title in existing_titles:
                        continue
                    
                    price = str(game_data.get('price', 'N/A')).strip()
                    gallery = game_data.get('gallery', [])
                    image_url = gallery[0] if gallery and len(gallery) > 0 else None
                    playtime = game_data.get('playtime_minutes', 60)
                    
                    game = Game(
                        title=title,
                        price=price,
                        image_url=image_url,
                        estimated_playtime_minutes=playtime or 60,
                        is_available=True,
                        full_data=game_data
                    )
                    
                    db.session.add(game)
                    existing_titles.add(title)
                    added_count += 1
                    
                    if added_count % 50 == 0:
                        db.session.commit()
                
                except Exception:
                    db.session.rollback()
                    continue
            
            if added_count > 0:
                db.session.commit()
                print(f"✅ Added {added_count} new games to database")
            else:
                print("✅ Database already up to date")
        
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        except Exception as e:
            print(f"⚠️ Error loading games: {e}")


# ============================================================================
# USER MANAGEMENT - FIXED
# ============================================================================
def get_current_user():
    """Get the current user from session or request parameters."""
    # First check Flask session (persistent)
    if 'user_id' in session:
        try:
            user = UserProfile.query.get(int(session['user_id']))
            if user:
                return user
        except (ValueError, TypeError):
            pass
    
    # Then check request args (URL parameter)
    user_id_arg = request.args.get('user_id')
    if user_id_arg:
        try:
            user = UserProfile.query.get(int(user_id_arg))
            if user:
                # Store in session for persistence
                session['user_id'] = int(user_id_arg)
                return user
        except (ValueError, TypeError):
            pass
    
    # Check form data
    user_id_form = request.form.get('user_id')
    if user_id_form:
        try:
            user = UserProfile.query.get(int(user_id_form))
            if user:
                session['user_id'] = int(user_id_form)
                return user
        except (ValueError, TypeError):
            pass
    
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
# CONTEXT PROCESSORS - Register user for all templates
# ============================================================================
@app.context_processor
def inject_user():
    """Make current user available in all templates."""
    user = get_current_user()
    return {
        'current_user': user,
        'user_id': session.get('user_id', request.args.get('user_id'))
    }


# ============================================================================
# VENUE MANAGEMENT
# ============================================================================
@app.route('/admin/venue', methods=['GET', 'POST'])
def manage_venue():
    """Admin: Manage venue capacity and settings."""
    try:
        venue = VenueConfig.get_or_create()
        
        if request.method == 'POST':
            try:
                venue.max_capacity = max(1, request.form.get('max_capacity', type=int, default=20))
                venue.max_tables = max(1, request.form.get('max_tables', type=int, default=5))
                venue.operating_hours_start = request.form.get('hours_start', type=int, default=10)
                venue.operating_hours_end = request.form.get('hours_end', type=int, default=22)
                db.session.commit()
                
                flash(f'Venue updated: {venue.max_capacity} max capacity', 'success')
                return redirect(url_for('manage_venue'))
            except ValueError as e:
                flash(f'Invalid input: {str(e)}', 'error')
        
        current_occupancy = venue.get_current_occupancy()
        occupancy_percent = int((current_occupancy / venue.max_capacity) * 100) if venue.max_capacity > 0 else 0
        
        return render_template(
            'venue_config.html',
            venue=venue,
            current_occupancy=current_occupancy,
            occupancy_percent=occupancy_percent
        )
    except Exception as e:
        flash(f'Error managing venue: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/api/venue/status')
def api_venue_status():
    """API: Get current venue occupancy status."""
    try:
        venue = VenueConfig.get_or_create()
        current_occupancy = venue.get_current_occupancy()
        max_cap = venue.max_capacity if venue.max_capacity > 0 else 1
        
        return jsonify({
            'max_capacity': venue.max_capacity,
            'current_occupancy': current_occupancy,
            'available_capacity': venue.available_capacity(),
            'occupancy_percent': int((current_occupancy / max_cap) * 100),
            'active_sessions': SessionLobby.query.filter_by(status=SessionStatus.ACTIVE.value).count(),
            'recruiting_sessions': SessionLobby.query.filter_by(status=SessionStatus.RECRUITING.value).count()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# AUTHENTICATION & USER PROFILES
# ============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login page."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
            return redirect(url_for('login'))
        
        try:
            user = UserProfile.query.filter_by(username=username).first()
            
            if not user:
                user = UserProfile(username=username, phone_number=phone_number)
                db.session.add(user)
                db.session.commit()
                flash(f'Welcome {username}!', 'success')
            else:
                if phone_number:
                    user.phone_number = phone_number
                    db.session.commit()
                flash(f'Welcome back {username}!', 'success')
            
            # Store user in session
            session['user_id'] = user.id
            session.permanent = True
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error logging in: {str(e)}', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))


@app.route('/profile/<int:user_id>')
def profile(user_id):
    """View user profile and credit history."""
    try:
        user = UserProfile.query.get_or_404(user_id)
        
        transactions = CreditTransaction.query.filter_by(user_id=user_id).order_by(
            CreditTransaction.created_at.desc()
        ).limit(20).all()
        
        recent_sessions = SessionParticipant.query.filter_by(user_id=user_id).order_by(
            SessionParticipant.joined_at.desc()
        ).limit(10).all()
        
        return render_template(
            'profile.html',
            user=user,
            transactions=transactions,
            recent_sessions=recent_sessions,
            user_id=user_id
        )
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'error')
        return redirect(url_for('login'))


# ============================================================================
# MAIN VIEWS
# ============================================================================
@app.route('/')
def index():
    """Redirect to login if no user, else to dashboard."""
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    """Main dashboard showing cafe floor status."""
    user = get_current_user()
    
    if not user:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    try:
        active_sessions = SessionLobby.query.filter_by(
            status=SessionStatus.ACTIVE.value
        ).all()
        recruiting_sessions = SessionLobby.query.filter_by(
            status=SessionStatus.RECRUITING.value
        ).all()
        
        example_sessions = []
        if not recruiting_sessions and not active_sessions:
            example_sessions = [{
                'game_name': 'Example: Catan',
                'slots_remaining': 3,
                'slots_total': 4,
                'status': SessionStatus.RECRUITING.value
            }]
        
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
        return render_template('dashboard.html', active=[], recruiting=[], example_sessions=[], user=user, user_stats={})


@app.route('/library')
def library():
    """Staff view of the physical game shelf."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    try:
        games = Game.query.order_by(Game.created_at.desc()).all()
        return render_template('library.html', games=games, user=user)
    except Exception as e:
        flash(f'Error loading library: {str(e)}', 'error')
        return render_template('library.html', games=[], user=user)


@app.route('/game/<int:game_id>')
def game_details(game_id):
    """Detailed view of a single game."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    try:
        game = Game.query.get_or_404(game_id)
        active_lobbies = SessionLobby.query.filter_by(
            game_id=game_id,
            status=SessionStatus.RECRUITING.value
        ).all()
        
        return render_template(
            'game_details.html',
            game=game,
            lobbies=active_lobbies,
            user=user
        )
    except Exception as e:
        flash(f'Error loading game details: {str(e)}', 'error')
        return redirect(url_for('library'))


# ============================================================================
# GAME MANAGEMENT
# ============================================================================
@app.route('/toggle_game/<int:game_id>', methods=['POST'])
def toggle_game(game_id):
    """Toggle game availability status."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
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
# SESSION MANAGEMENT
# ============================================================================
@app.route('/session/<int:session_id>')
def view_session(session_id):
    """View details of a specific session."""
    try:
        user = get_current_user()
        session_obj = SessionLobby.query.get_or_404(session_id)
        
        if not session_obj.game:
            flash('Game information unavailable', 'error')
            return redirect(url_for('dashboard'))
        
        session_info = {
            'can_join': session_obj.status == SessionStatus.RECRUITING.value and not session_obj.is_full,
            'is_participant': user and any(p.user_id == user.id for p in session_obj.participants),
            'is_host': user and user.id == session_obj.host_id,
            'time_remaining': session_obj.time_remaining_minutes if session_obj.status == SessionStatus.ACTIVE.value else None,
            'is_overdue': session_obj.is_overdue,
            'estimated_end_time': session_obj.estimated_end_time,
            'session_duration': session_obj.estimated_duration_minutes
        }
        
        return render_template(
            'view_session.html',
            session=session_obj,
            user=user,
            session_info=session_info
        )
    except Exception as e:
        flash(f'Error loading session: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/session/create', methods=['GET', 'POST'])
@require_user
def create_session(user):
    """Create a new LFG session."""
    try:
        venue = VenueConfig.get_or_create()
        # min_date removed to relax validation
        
        if request.method == 'POST':
            game_id = request.form.get('game_id', type=int)
            slots_total = request.form.get('slots_total', type=int, default=4)
            estimated_duration = request.form.get('estimated_duration_minutes', type=int)
            
            game = Game.query.get(game_id)
            if not game:
                flash('Invalid game selected', 'error')
                games = Game.query.all()
                return render_template('create_session.html', games=games, user=user, available_capacity=venue.available_capacity())
            
            if slots_total < 2 or slots_total > 10:
                flash('Players must be between 2 and 10', 'error')
                games = Game.query.all()
                return render_template('create_session.html', games=games, user=user, available_capacity=venue.available_capacity())
            
            # Check capacity
            if not venue.can_accommodate(slots_total):
                flash(f'Venue capacity exceeded. Only {venue.available_capacity()} seats available', 'error')
                games = Game.query.all()
                return render_template('create_session.html', games=games, user=user, available_capacity=venue.available_capacity())
            
            # Parse scheduled start time
            scheduled_start_time = request.form.get('scheduled_start_time')
            start_time_obj = None
            if scheduled_start_time:
                try:
                    start_time_obj = datetime.fromisoformat(scheduled_start_time)
                except ValueError:
                    pass  # Invalid format, ignore or handle error

            session_obj = SessionLobby(
                game_id=game_id,
                slots_total=slots_total,
                slots_filled=1,
                status=SessionStatus.RECRUITING.value,
                host_id=user.id,
                estimated_duration_minutes=estimated_duration or (game.estimated_playtime_minutes or 60),
                scheduled_start_time=start_time_obj
            )
            db.session.add(session_obj)
            db.session.flush()
            
            participant = SessionParticipant(session_id=session_obj.id, user_id=user.id)
            session_obj.participants.append(participant)
            
            db.session.commit()
            
            flash(f'Session created for {game.title}!', 'success')
            return redirect(url_for('view_session', session_id=session_obj.id))
        
        games = Game.query.filter_by(is_available=True).all()
        if not games:
            games = Game.query.all()
        # Removed client-side min_date validation to avoid "invalid value" errors
        
        return render_template(
            'create_session.html',
            games=games,
            user=user,
            available_capacity=venue.available_capacity()
        )
    
    except Exception as e:
        flash(f'Error creating session: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/session/<int:session_id>/join', methods=['POST'])
@require_user
def join_session(session_id, user):
    """Join an existing session."""
    try:
        session_obj = SessionLobby.query.get_or_404(session_id)
        
        if session_obj.status != SessionStatus.RECRUITING.value:
            flash('This session is not recruiting', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        if session_obj.is_full:
            flash('Session is full', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        if any(p.user_id == user.id for p in session_obj.participants):
            flash('You are already in this session', 'warning')
            return redirect(url_for('view_session', session_id=session_id))
        
        session_obj.add_participant(user)
        db.session.commit()
        
        flash('Joined session!', 'success')
        return redirect(url_for('view_session', session_id=session_id))
    
    except ValueError as e:
        flash(f'Cannot join: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id))
    except Exception as e:
        flash(f'Error joining session: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/session/<int:session_id>/leave', methods=['POST'])
@require_user
def leave_session(session_id, user):
    """Leave a session."""
    try:
        session_obj = SessionLobby.query.get_or_404(session_id)
        
        if session_obj.host_id == user.id and session_obj.status == SessionStatus.ACTIVE.value:
            flash('Host cannot leave an active session', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        session_obj.remove_participant(user)
        db.session.commit()
        
        flash('Left session', 'success')
        return redirect(url_for('view_session', session_id=session_id))
    
    except Exception as e:
        flash(f'Error leaving session: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/session/<int:session_id>/start', methods=['POST'])
@require_user
def start_session(session_id, user):
    """Start a session."""
    try:
        session_obj = SessionLobby.query.get_or_404(session_id)
        
        if session_obj.host_id != user.id:
            flash('Only the host can start the session', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        if not session_obj.can_start:
            flash(f'Need at least 2 players. Currently {session_obj.slots_filled}', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        venue = VenueConfig.get_or_create()
        if not venue.can_accommodate(session_obj.slots_filled):
            flash(f'Cannot start: Venue at capacity. Only {venue.available_capacity()} seats available', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        session_obj.status = SessionStatus.ACTIVE.value
        session_obj.started_at = datetime.utcnow()
        db.session.commit()
        
        flash('Session started! Have fun!', 'success')
        return redirect(url_for('view_session', session_id=session_id))
    
    except Exception as e:
        flash(f'Error starting session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id))


@app.route('/session/<int:session_id>/complete', methods=['POST'])
@require_user
def complete_session(session_id, user):
    """Complete a session and award credits."""
    try:
        session_obj = SessionLobby.query.get_or_404(session_id)
        
        if session_obj.host_id != user.id:
            flash('Only the host can complete the session', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        session_obj.complete_session()
        db.session.commit()
        
        flash('Session completed! Credits awarded to all participants.', 'success')
        return redirect(url_for('dashboard'))
    
    except ValueError as e:
        flash(f'Cannot complete: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id))
    except Exception as e:
        flash(f'Error completing session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id))


@app.route('/session/<int:session_id>/cancel', methods=['POST'])
@require_user
def cancel_session(session_id, user):
    """Cancel a session."""
    try:
        session_obj = SessionLobby.query.get_or_404(session_id)
        
        if session_obj.host_id != user.id:
            flash('Only the host can cancel the session', 'error')
            return redirect(url_for('view_session', session_id=session_id))
        
        session_obj.status = SessionStatus.CANCELLED.value
        db.session.commit()
        
        flash('Session cancelled', 'success')
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        flash(f'Error cancelling session: {str(e)}', 'error')
        return redirect(url_for('view_session', session_id=session_id))


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
    
    try:
        transactions = CreditTransaction.query.filter_by(user_id=user.id).order_by(
            CreditTransaction.created_at.desc()
        ).limit(50).all()
        
        return render_template('credits.html', user=user, transactions=transactions)
    except Exception as e:
        flash(f'Error loading credits: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


# ============================================================================
# API ENDPOINTS
# ============================================================================
@app.route('/api/sessions')
def api_sessions():
    """Get all recruiting sessions as JSON."""
    try:
        sessions_list = SessionLobby.query.filter_by(
            status=SessionStatus.RECRUITING.value
        ).all()
        
        data = [{
            'id': s.id,
            'game': s.game.title if s.game else 'Unknown',
            'host': s.host.username if s.host else 'Unknown',
            'slots_filled': s.slots_filled,
            'slots_total': s.slots_total,
            'created_at': s.created_at.isoformat()
        } for s in sessions_list]
        
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
# APPLICATION ENTRY POINT
# ============================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        load_games_from_json()#
    app.run(host='0.0.0.0', port=5000, debug=True)