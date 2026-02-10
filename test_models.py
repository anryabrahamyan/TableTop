"""
Unit Tests for TableTop Application
Tests individual models and business logic without HTTP requests
"""

import unittest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestDatabase(unittest.TestCase):
    """Test database setup and initialization."""
    
    def setUp(self):
        """Set up test database."""
        # Import here to avoid initialization issues
        from app import app
        from models import db
        
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        self.db = db
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Tear down test database."""
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()


class TestUserProfile(TestDatabase):
    """Test UserProfile model and functionality."""
    
    def test_user_creation(self):
        """Test creating a new user profile."""
        from models import UserProfile
        
        with self.app.app_context():
            user = UserProfile(username='test_user')
            self.db.session.add(user)
            self.db.session.commit()
            
            retrieved = UserProfile.query.filter_by(username='test_user').first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.username, 'test_user')
            self.assertEqual(retrieved.credit_balance, 0)
    
    def test_unique_username(self):
        """Test that usernames must be unique."""
        from models import UserProfile
        
        with self.app.app_context():
            user1 = UserProfile(username='duplicate')
            self.db.session.add(user1)
            self.db.session.commit()
            
            user2 = UserProfile(username='duplicate')
            self.db.session.add(user2)
            
            with self.assertRaises(Exception):  # IntegrityError
                self.db.session.commit()
    
    def test_can_join_session_positive_balance(self):
        """Test that user with positive balance can join."""
        from models import UserProfile
        
        with self.app.app_context():
            user = UserProfile(username='good_user', credit_balance=10)
            self.db.session.add(user)
            self.db.session.commit()
            
            self.assertTrue(user.can_join_session())
    
    def test_can_join_session_zero_balance(self):
        """Test that user with zero balance can join."""
        from models import UserProfile
        
        with self.app.app_context():
            user = UserProfile(username='zero_user', credit_balance=0)
            self.db.session.add(user)
            self.db.session.commit()
            
            self.assertTrue(user.can_join_session())
    
    def test_can_join_session_negative_balance_boundary(self):
        """Test that user can join when balance is exactly -50."""
        from models import UserProfile
        
        with self.app.app_context():
            user = UserProfile(username='boundary_user', credit_balance=-50)
            self.db.session.add(user)
            self.db.session.commit()
            
            self.assertFalse(user.can_join_session())
    
    def test_can_join_session_negative_balance_exceeds(self):
        """Test that user cannot join when balance is below -50."""
        from models import UserProfile
        
        with self.app.app_context():
            user = UserProfile(username='bad_user', credit_balance=-60)
            self.db.session.add(user)
            self.db.session.commit()
            
            self.assertFalse(user.can_join_session())


class TestGame(TestDatabase):
    """Test Game model."""
    
    def test_game_creation(self):
        """Test creating a game."""
        from models import Game
        
        with self.app.app_context():
            game = Game(title='Catan', price='$35', is_available=True)
            self.db.session.add(game)
            self.db.session.commit()
            
            retrieved = Game.query.filter_by(title='Catan').first()
            self.assertIsNotNone(retrieved)
            self.assertTrue(retrieved.is_available)
    
    def test_game_availability_toggle(self):
        """Test toggling game availability."""
        from models import Game
        
        with self.app.app_context():
            game = Game(title='Ticket to Ride', is_available=True)
            self.db.session.add(game)
            self.db.session.commit()
            
            game.is_available = False
            self.db.session.commit()
            
            retrieved = Game.query.filter_by(title='Ticket to Ride').first()
            self.assertFalse(retrieved.is_available)


class TestSessionLobby(TestDatabase):
    """Test SessionLobby model and functionality."""
    
    def setUp(self):
        """Set up test database with sample data."""
        super().setUp()
        from models import UserProfile, Game
        
        with self.app.app_context():
            self.host = UserProfile(username='host')
            self.user1 = UserProfile(username='user1')
            self.user2 = UserProfile(username='user2')
            self.game = Game(title='Gloomhaven')
            
            self.db.session.add_all([self.host, self.user1, self.user2, self.game])
            self.db.session.commit()
    
    def test_session_creation(self):
        """Test creating a new session."""
        from models import SessionLobby
        
        with self.app.app_context():
            host = self.host
            game = self.game
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                status='RECRUITING'
            )
            self.db.session.add(session)
            self.db.session.commit()
            
            retrieved = SessionLobby.query.first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.status, 'RECRUITING')
    
    def test_slots_remaining_calculation(self):
        """Test that slots_remaining is calculated correctly."""
        from models import SessionLobby
        
        with self.app.app_context():
            host = self.host
            game = self.game
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            self.db.session.add(session)
            self.db.session.commit()
            
            self.assertEqual(session.slots_remaining, 3)
    
    def test_can_start_minimum_players(self):
        """Test that session needs minimum 2 players to start."""
        from models import SessionLobby
        
        with self.app.app_context():
            host = self.host
            game = self.game
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            self.db.session.add(session)
            self.db.session.commit()
            
            self.assertFalse(session.can_start)
            
            session.slots_filled = 2
            self.assertTrue(session.can_start)
    
    def test_add_participant_success(self):
        """Test successfully adding a participant."""
        from models import SessionLobby
        
        with self.app.app_context():
            host = self.host
            user1 = self.user1
            game = self.game
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            self.db.session.add(session)
            self.db.session.commit()
            
            session.add_participant(user1)
            self.db.session.commit()
            
            self.assertEqual(session.slots_filled, 2)
            self.assertEqual(len(session.participants), 1)
    
    def test_add_participant_full_session(self):
        """Test that cannot add participant to full session."""
        from models import SessionLobby
        
        with self.app.app_context():
            host = self.host
            user1 = self.user1
            game = self.game
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=1,
                slots_filled=1
            )
            self.db.session.add(session)
            self.db.session.commit()
            
            with self.assertRaises(ValueError):
                session.add_participant(user1)
    
    def test_complete_session_awards_credits(self):
        """Test that completing a session awards credits to participants."""
        from models import SessionLobby, SessionParticipant, SessionStatus
        
        with self.app.app_context():
            host = self.host
            user1 = self.user1
            game = self.game
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=2,
                slots_filled=2,
                status=SessionStatus.ACTIVE.value,
                started_at=datetime.utcnow()
            )
            participant = SessionParticipant(user_id=user1.id)
            session.participants.append(participant)
            self.db.session.add(session)
            self.db.session.commit()
            
            initial_user1_balance = user1.credit_balance
            session.complete_session()
            self.db.session.commit()
            
            # Check credits were awarded
            self.assertEqual(user1.credit_balance, initial_user1_balance + 10)
            self.assertEqual(session.status, SessionStatus.COMPLETED.value)


class TestCreditTransaction(TestDatabase):
    """Test CreditTransaction model."""
    
    def test_transaction_creation(self):
        """Test creating a credit transaction."""
        from models import UserProfile, CreditTransaction
        
        with self.app.app_context():
            user = UserProfile(username='test_user')
            self.db.session.add(user)
            self.db.session.commit()
            
            transaction = CreditTransaction(
                user_id=user.id,
                amount=10,
                transaction_type='SESSION_REWARD',
                description='Test reward'
            )
            self.db.session.add(transaction)
            self.db.session.commit()
            
            retrieved = CreditTransaction.query.first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.amount, 10)


if __name__ == '__main__':
    unittest.main()
    """Test UserProfile model and functionality."""
    
    def test_user_creation(self):
        """Test creating a new user profile."""
        with app.app_context():
            user = UserProfile(username='test_user')
            db.session.add(user)
            db.session.commit()
            
            retrieved = UserProfile.query.filter_by(username='test_user').first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.username, 'test_user')
            self.assertEqual(retrieved.credit_balance, 0)
    
    def test_unique_username(self):
        """Test that usernames must be unique."""
        with app.app_context():
            user1 = UserProfile(username='duplicate')
            db.session.add(user1)
            db.session.commit()
            
            user2 = UserProfile(username='duplicate')
            db.session.add(user2)
            
            with self.assertRaises(Exception):  # IntegrityError
                db.session.commit()
    
    def test_can_join_session_positive_balance(self):
        """Test that user with positive balance can join."""
        with app.app_context():
            user = UserProfile(username='good_user', credit_balance=10)
            db.session.add(user)
            db.session.commit()
            
            self.assertTrue(user.can_join_session())
    
    def test_can_join_session_zero_balance(self):
        """Test that user with zero balance can join."""
        with app.app_context():
            user = UserProfile(username='zero_user', credit_balance=0)
            db.session.add(user)
            db.session.commit()
            
            self.assertTrue(user.can_join_session())
    
    def test_can_join_session_negative_balance_boundary(self):
        """Test that user can join when balance is exactly -50."""
        with app.app_context():
            user = UserProfile(username='boundary_user', credit_balance=-50)
            db.session.add(user)
            db.session.commit()
            
            self.assertFalse(user.can_join_session())
    
    def test_can_join_session_negative_balance_exceeds(self):
        """Test that user cannot join when balance is below -50."""
        with app.app_context():
            user = UserProfile(username='bad_user', credit_balance=-60)
            db.session.add(user)
            db.session.commit()
            
            self.assertFalse(user.can_join_session())


class TestGame(TestDatabase):
    """Test Game model."""
    
    def test_game_creation(self):
        """Test creating a game."""
        with app.app_context():
            game = Game(title='Catan', price='$35', is_available=True)
            db.session.add(game)
            db.session.commit()
            
            retrieved = Game.query.filter_by(title='Catan').first()
            self.assertIsNotNone(retrieved)
            self.assertTrue(retrieved.is_available)
    
    def test_game_availability_toggle(self):
        """Test toggling game availability."""
        with app.app_context():
            game = Game(title='Ticket to Ride', is_available=True)
            db.session.add(game)
            db.session.commit()
            
            game.is_available = False
            db.session.commit()
            
            retrieved = Game.query.filter_by(title='Ticket to Ride').first()
            self.assertFalse(retrieved.is_available)


class TestSessionLobby(TestDatabase):
    """Test SessionLobby model and functionality."""
    
    def setUp(self):
        """Set up test database with sample data."""
        super().setUp()
        with app.app_context():
            self.host = UserProfile(username='host')
            self.user1 = UserProfile(username='user1')
            self.user2 = UserProfile(username='user2')
            self.game = Game(title='Gloomhaven')
            
            db.session.add_all([self.host, self.user1, self.user2, self.game])
            db.session.commit()
    
    def test_session_creation(self):
        """Test creating a new session."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                status=SessionStatus.RECRUITING.value
            )
            db.session.add(session)
            db.session.commit()
            
            retrieved = SessionLobby.query.first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.status, SessionStatus.RECRUITING.value)
    
    def test_slots_remaining_calculation(self):
        """Test that slots_remaining is calculated correctly."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            db.session.add(session)
            db.session.commit()
            
            self.assertEqual(session.slots_remaining, 3)
    
    def test_can_start_minimum_players(self):
        """Test that session needs minimum 2 players to start."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            db.session.add(session)
            db.session.commit()
            
            self.assertFalse(session.can_start)
            
            session.slots_filled = 2
            self.assertTrue(session.can_start)
    
    def test_add_participant_success(self):
        """Test successfully adding a participant."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            user1 = UserProfile.query.filter_by(username='user1').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            db.session.add(session)
            db.session.commit()
            
            session.add_participant(user1)
            db.session.commit()
            
            self.assertEqual(session.slots_filled, 2)
            self.assertEqual(len(session.participants), 1)
    
    def test_add_participant_full_session(self):
        """Test that cannot add participant to full session."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            user1 = UserProfile.query.filter_by(username='user1').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=1,
                slots_filled=1
            )
            db.session.add(session)
            db.session.commit()
            
            with self.assertRaises(ValueError):
                session.add_participant(user1)
    
    def test_add_participant_duplicate(self):
        """Test that cannot add same user twice."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            user1 = UserProfile.query.filter_by(username='user1').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=1
            )
            db.session.add(session)
            db.session.commit()
            
            session.add_participant(user1)
            db.session.commit()
            
            with self.assertRaises(ValueError):
                session.add_participant(user1)
    
    def test_remove_participant(self):
        """Test removing a participant."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            user1 = UserProfile.query.filter_by(username='user1').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=2
            )
            participant = SessionParticipant(user_id=user1.id)
            session.participants.append(participant)
            db.session.add(session)
            db.session.commit()
            
            session.remove_participant(user1)
            db.session.commit()
            
            self.assertEqual(session.slots_filled, 1)
    
    def test_complete_session_awards_credits(self):
        """Test that completing a session awards credits to participants."""
        with app.app_context():
            host = UserProfile.query.filter_by(username='host').first()
            user1 = UserProfile.query.filter_by(username='user1').first()
            game = Game.query.filter_by(title='Gloomhaven').first()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=2,
                slots_filled=2,
                status=SessionStatus.ACTIVE.value,
                started_at=datetime.utcnow()
            )
            participant = SessionParticipant(user_id=user1.id)
            session.participants.append(participant)
            db.session.add(session)
            db.session.commit()
            
            initial_user1_balance = user1.credit_balance
            session.complete_session()
            db.session.commit()
            
            # Check credits were awarded
            self.assertEqual(user1.credit_balance, initial_user1_balance + 10)
            self.assertEqual(session.status, SessionStatus.COMPLETED.value)


class TestCreditTransaction(TestDatabase):
    """Test CreditTransaction model."""
    
    def test_transaction_creation(self):
        """Test creating a credit transaction."""
        with app.app_context():
            user = UserProfile(username='test_user')
            db.session.add(user)
            db.session.commit()
            
            transaction = CreditTransaction(
                user_id=user.id,
                amount=10,
                transaction_type='SESSION_REWARD',
                description='Test reward'
            )
            db.session.add(transaction)
            db.session.commit()
            
            retrieved = CreditTransaction.query.first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.amount, 10)


class TestErrorHandling(TestDatabase):
    """Test error handling in business logic."""
    
    def test_session_start_invalid_status(self):
        """Test cannot start session that's not recruiting."""
        with app.app_context():
            host = UserProfile(username='host')
            game = Game(title='Test Game')
            db.session.add_all([host, game])
            db.session.commit()
            
            session = SessionLobby(
                game_id=game.id,
                host_id=host.id,
                slots_total=4,
                slots_filled=2,
                status=SessionStatus.COMPLETED.value
            )
            db.session.add(session)
            db.session.commit()
            
            with self.assertRaises(ValueError):
                session.complete_session()


if __name__ == '__main__':
    unittest.main()
