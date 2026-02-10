from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from enum import Enum

db = SQLAlchemy()


# ============================================================================
# 1. INTERNAL GAME REGISTRY (FR.1.2)
# ============================================================================
class Game(db.Model):
    """Represents a board game in the physical library."""
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(50))
    image_url = db.Column(db.String(512))
    is_available = db.Column(db.Boolean, default=True)  # Staff Toggle support
    
    # Store the entire HobbyGames JSON object (NoSQL style)
    full_data = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Game {self.title}>'


# ============================================================================
# 2. USER IDENTITY & CREDIT ENGINE (FR.1.1 & FR.4.1)
# ============================================================================
class UserProfile(db.Model):
    """Represents a user/player in the system."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    credit_balance = db.Column(db.Integer, default=0)  # Negative credits represent debt
    reliability_streak = db.Column(db.Integer, default=0)  # Consecutive completed sessions
    sessions_completed = db.Column(db.Integer, default=0)
    sessions_cancelled = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    session_registrations = db.relationship('SessionParticipant', backref='user', cascade='all, delete-orphan')
    transactions = db.relationship('CreditTransaction', backref='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UserProfile {self.username}>'
    
    def can_join_session(self):
        """Check if user meets eligibility criteria to join a session."""
        # User cannot join if they have negative credit balance > -50
        return self.credit_balance > -50


# ============================================================================
# 3. SESSION & LFG LOGIC (FR.2.1)
# ============================================================================
class SessionStatus(Enum):
    """Enumeration for session states."""
    RECRUITING = 'RECRUITING'  # Waiting for players
    ACTIVE = 'ACTIVE'          # Game in progress
    COMPLETED = 'COMPLETED'    # Game finished
    CANCELLED = 'CANCELLED'    # Session cancelled


class SessionLobby(db.Model):
    """Represents a table session/LFG group."""
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    table_number = db.Column(db.Integer)
    status = db.Column(db.String(20), default=SessionStatus.RECRUITING.value)
    slots_total = db.Column(db.Integer, nullable=False)
    slots_filled = db.Column(db.Integer, default=1)
    
    # Session timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    estimated_duration_minutes = db.Column(db.Integer, default=60)
    
    # Host/organizer
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    host = db.relationship('UserProfile', foreign_keys=[host_id], backref='hosted_sessions')
    
    # Relationships
    game = db.relationship('Game', backref='lobbies')
    participants = db.relationship('SessionParticipant', backref='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<SessionLobby {self.id} - {self.game.title if self.game else "Unknown"} ({self.status})>'
    
    @property
    def slots_remaining(self):
        """Calculate remaining player slots."""
        return self.slots_total - self.slots_filled if self.slots_total else 0
    
    @property
    def can_start(self):
        """Check if session has minimum players to start."""
        return self.slots_filled >= 2  # Minimum 2 players
    
    @property
    def is_full(self):
        """Check if session has reached max capacity."""
        return self.slots_filled >= self.slots_total
    
    def add_participant(self, user):
        """Add a participant to the session."""
        if self.is_full:
            raise ValueError("Session is full")
        if any(p.user_id == user.id for p in self.participants):
            raise ValueError("User already in this session")
        if not user.can_join_session():
            raise ValueError("User does not meet eligibility criteria")
        
        participant = SessionParticipant(session_id=self.id, user_id=user.id)
        self.participants.append(participant)
        self.slots_filled += 1
        return participant
    
    def remove_participant(self, user):
        """Remove a participant from the session."""
        participant = SessionParticipant.query.filter_by(
            session_id=self.id, user_id=user.id
        ).first()
        if participant:
            self.participants.remove(participant)
            self.slots_filled = max(1, self.slots_filled - 1)
            db.session.delete(participant)
    
    def complete_session(self):
        """Mark session as completed and award credits."""
        if self.status != SessionStatus.ACTIVE.value:
            raise ValueError("Only active sessions can be completed")
        
        self.status = SessionStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        
        # Award credits to all participants
        for participant in self.participants:
            participant.user.sessions_completed += 1
            participant.user.reliability_streak += 1
            
            # Base reward for participation
            reward = 10
            participant.user.credit_balance += reward
            
            # Transaction log
            transaction = CreditTransaction(
                user_id=participant.user_id,
                amount=reward,
                transaction_type='SESSION_REWARD',
                description=f'Completed session #{self.id} - {self.game.title}'
            )
            db.session.add(transaction)
        
        return True


# ============================================================================
# 4. SESSION PARTICIPANTS (Junction Table for Sessions & Users)
# ============================================================================
class SessionParticipant(db.Model):
    """Junction table linking users to sessions."""
    __tablename__ = 'session_participants'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE, COMPLETED, CANCELLED
    
    def __repr__(self):
        return f'<SessionParticipant user_id={self.user_id} session_id={self.session_id}>'


# ============================================================================
# 5. CREDIT SYSTEM / FINANCIAL LEDGER (FR.4.1)
# ============================================================================
class CreditTransaction(db.Model):
    """Audit trail for all credit movements."""
    __tablename__ = 'credit_transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Positive = credit gain, Negative = credit spent
    transaction_type = db.Column(db.String(50), nullable=False)  # SESSION_REWARD, MANUAL_ADJUSTMENT, PENALTY, etc.
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CreditTransaction user_id={self.user_id} amount={self.amount} type={self.transaction_type}>'