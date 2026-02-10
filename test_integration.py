"""
Integration Tests for TableTop Application
Tests HTTP requests and full user flows
"""

import unittest
from models import db, Game, UserProfile, SessionLobby, SessionStatus
from app import app


class TestIntegration(unittest.TestCase):
    """Integration tests for HTTP endpoints."""
    
    def setUp(self):
        """Set up test client and database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # Create test data
            self.host_user = UserProfile(username='host')
            self.player1 = UserProfile(username='player1')
            self.player2 = UserProfile(username='player2')
            self.game = Game(title='Catan', is_available=True)
            
            db.session.add_all([self.host_user, self.player1, self.player2, self.game])
            db.session.commit()
        
        self.client = app.test_client()
    
    def tearDown(self):
        """Tear down test database."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_login_page_loads(self):
        """Test that login page loads."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TableTop', response.data)
    
    def test_login_creates_user(self):
        """Test that logging in creates a new user."""
        response = self.client.post('/login', data={'username': 'newuser'})
        
        with app.app_context():
            user = UserProfile.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
    
    def test_login_existing_user(self):
        """Test that logging in existing user works."""
        response = self.client.post('/login', data={'username': 'host'})
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_dashboard_requires_user_id(self):
        """Test that dashboard redirects without user_id."""
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_with_user(self):
        """Test dashboard loads with valid user."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            response = self.client.get(f'/dashboard?user_id={host.id}')
            self.assertEqual(response.status_code, 200)
    
    def test_library_page_loads(self):
        """Test that library page loads."""
        response = self.client.get('/library')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Catan', response.data)
    
    def test_game_details_page(self):
        """Test that game details page loads."""
        with app.app_context():
            game = Game.query.filter_by(title='Catan').first()
            response = self.client.get(f'/game/{game.id}')
            self.assertEqual(response.status_code, 200)
    
    def test_game_details_404(self):
        """Test that game details returns 404 for invalid game."""
        response = self.client.get('/game/99999')
        self.assertEqual(response.status_code, 404)
    
    def test_toggle_game_availability(self):
        """Test toggling game availability."""
        with app.app_context():
            game = Game.query.filter_by(title='Catan').first()
            initial_state = game.is_available
            
            response = self.client.post(f'/toggle_game/{game.id}')
            
            updated_game = Game.query.filter_by(title='Catan').first()
            self.assertNotEqual(updated_game.is_available, initial_state)
    
    def test_create_session_page_requires_user(self):
        """Test that create session requires user."""
        response = self.client.get('/session/create')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_create_session_with_user(self):
        """Test creating a session."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            game = Game.query.filter_by(title='Catan').first()
            
            response = self.client.post(
                f'/session/create?user_id={host.id}',
                data={'game_id': game.id, 'slots_total': 4}
            )
            
            # Check session was created
            session = SessionLobby.query.first()
            self.assertIsNotNone(session)
            self.assertEqual(session.host_id, host.id)
    
    def test_view_session(self):
        """Test viewing a session."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            game = Game.query.filter_by(title='Catan').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1,
                status=SessionStatus.RECRUITING.value
            )
            db.session.add(session)
            db.session.commit()
            
            response = self.client.get(f'/session/{session.id}')
            self.assertEqual(response.status_code, 200)
    
    def test_join_session(self):
        """Test joining a session."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            player = UserProfile.query.filter_by(username='player1').first()
            game = Game.query.filter_by(title='Catan').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1,
                status=SessionStatus.RECRUITING.value
            )
            db.session.add(session)
            db.session.commit()
            session_id = session.id
            
            response = self.client.post(
                f'/session/{session_id}/join?user_id={player.id}'
            )
            
            # Check player was added
            session = SessionLobby.query.get(session_id)
            self.assertEqual(session.slots_filled, 2)
    
    def test_leave_session(self):
        """Test leaving a session."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            player = UserProfile.query.filter_by(username='player1').first()
            game = Game.query.filter_by(title='Catan').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=2,
                status=SessionStatus.RECRUITING.value
            )
            from models import SessionParticipant
            participant = SessionParticipant(session_id=None, user_id=player.id)
            session.participants.append(participant)
            db.session.add(session)
            db.session.commit()
            session_id = session.id
            
            response = self.client.post(
                f'/session/{session_id}/leave?user_id={player.id}'
            )
            
            # Check player was removed
            session = SessionLobby.query.get(session_id)
            self.assertEqual(session.slots_filled, 1)
    
    def test_start_session_by_host(self):
        """Test starting a session (host only)."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            player = UserProfile.query.filter_by(username='player1').first()
            game = Game.query.filter_by(title='Catan').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=2,
                status=SessionStatus.RECRUITING.value
            )
            from models import SessionParticipant
            participant = SessionParticipant(session_id=None, user_id=player.id)
            session.participants.append(participant)
            db.session.add(session)
            db.session.commit()
            session_id = session.id
            
            response = self.client.post(
                f'/session/{session_id}/start?user_id={host.id}'
            )
            
            # Check status changed
            session = SessionLobby.query.get(session_id)
            self.assertEqual(session.status, SessionStatus.ACTIVE.value)
    
    def test_profile_page(self):
        """Test viewing user profile."""
        with app.app_context():
            user = UserProfile.query.filter_by(username='host').first()
            response = self.client.get(f'/profile/{user.id}')
            self.assertEqual(response.status_code, 200)
    
    def test_credits_page(self):
        """Test viewing credits page."""
        with app.app_context():
            user = UserProfile.query.filter_by(username='host').first()
            response = self.client.get(f'/credits?user_id={user.id}')
            self.assertEqual(response.status_code, 200)
    
    def test_api_sessions_endpoint(self):
        """Test API endpoint for sessions."""
        response = self.client.get('/api/sessions')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
    
    def test_api_user_endpoint(self):
        """Test API endpoint for user info."""
        with app.app_context():
            user = UserProfile.query.filter_by(username='host').first()
            response = self.client.get(f'/api/user/{user.id}')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['username'], 'host')
    
    def test_404_error_handling(self):
        """Test 404 error handling."""
        response = self.client.get('/nonexistent/page')
        self.assertEqual(response.status_code, 404)


class TestValidation(unittest.TestCase):
    """Test input validation."""
    
    def setUp(self):
        """Set up test client."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
        
        self.client = app.test_client()
    
    def tearDown(self):
        """Tear down test database."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_login_username_too_short(self):
        """Test that username must be at least 3 characters."""
        response = self.client.post('/login', data={'username': 'ab'})
        self.assertEqual(response.status_code, 302)  # Should redirect
    
    def test_create_session_invalid_game(self):
        """Test that creating session with invalid game fails."""
        with app.app_context():
            user = UserProfile(username='test')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            
            response = self.client.post(
                f'/session/create?user_id={user_id}',
                data={'game_id': 99999, 'slots_total': 4}
            )
            
            # Session should not be created
            self.assertEqual(SessionLobby.query.count(), 0)
    
    def test_create_session_invalid_slots(self):
        """Test that slots must be between 2 and 10."""
        with app.app_context():
            user = UserProfile(username='test')
            game = Game(title='Test Game')
            db.session.add_all([user, game])
            db.session.commit()
            user_id = user.id
            game_id = game.id
            
            # Too few slots
            response = self.client.post(
                f'/session/create?user_id={user_id}',
                data={'game_id': game_id, 'slots_total': 1}
            )
            
            # Session should not be created
            self.assertEqual(SessionLobby.query.count(), 0)
            
            # Too many slots
            response = self.client.post(
                f'/session/create?user_id={user_id}',
                data={'game_id': game_id, 'slots_total': 20}
            )
            
            # Session should not be created
            self.assertEqual(SessionLobby.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
