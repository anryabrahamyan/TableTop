from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta
from enum import Enum

db = SQLAlchemy()

# ============================================================================
# VENUE CONFIGURATION
# ============================================================================
class VenueConfig(db.Model):
    """Cafe venue configuration and capacity settings."""
    __tablename__ = 'venue_config'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), default='TableTop Cafe #001')
    max_capacity = db.Column(db.Integer, default=20)
    max_tables = db.Column(db.Integer, default=5)
    operating_hours_start = db.Column(db.Integer, default=10)
    operating_hours_end = db.Column(db.Integer, default=22)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<VenueConfig {self.name} - Capacity: {self.max_capacity}>'
    
    @classmethod
    def get_or_create(cls):
        """Get or create default venue config."""
        config = cls.query.first()
        if not config:
            config = cls()
            db.session.add(config)
            db.session.commit()
        return config
    
    def get_current_occupancy(self):
        """Get current number of players in active sessions."""
        active_sessions = SessionLobby.query.filter_by(
            status=SessionStatus.ACTIVE.value
        ).all()
        return sum(s.slots_filled for s in active_sessions) if active_sessions else 0
    
    def can_accommodate(self, additional_players):
        """Check if venue can accommodate additional players."""
        return self.get_current_occupancy() + additional_players <= self.max_capacity
    
    def available_capacity(self):
        """Get remaining capacity."""
        return max(0, self.max_capacity - self.get_current_occupancy())


# ============================================================================
# SESSION STATUS (Define before using)
# ============================================================================
class SessionStatus(Enum):
    """Enumeration for session states."""
    RECRUITING = 'RECRUITING'
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'


# ============================================================================
# GAME REGISTRY
# ============================================================================
class Game(db.Model):
    """Represents a board game in the physical library."""
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, unique=True)
    price = db.Column(db.String(50))
    image_url = db.Column(db.String(512))
    is_available = db.Column(db.Boolean, default=True)
    estimated_playtime_minutes = db.Column(db.Integer, default=60)
    full_data = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Game {self.title}>'


# ============================================================================
# USER PROFILE
# ============================================================================
class UserProfile(db.Model):
    """Represents a user/player in the system."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True)
    phone_number = db.Column(db.String(20))
    credit_balance = db.Column(db.Integer, default=0)
    reliability_streak = db.Column(db.Integer, default=0)
    sessions_completed = db.Column(db.Integer, default=0)
    sessions_cancelled = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    session_registrations = db.relationship('SessionParticipant', backref='user', cascade='all, delete-orphan')
    transactions = db.relationship('CreditTransaction', backref='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UserProfile {self.username}>'
    
    def can_join_session(self):
        """Check if user meets eligibility criteria to join a session."""
        return self.credit_balance > -50


# ============================================================================
# SESSION LOBBY
# ============================================================================
class SessionLobby(db.Model):
    """Represents a table session/LFG group."""
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    table_number = db.Column(db.Integer)
    status = db.Column(db.String(20), default=SessionStatus.RECRUITING.value, nullable=False)
    slots_total = db.Column(db.Integer, nullable=False)
    slots_filled = db.Column(db.Integer, default=1)
    
    # Session timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    scheduled_start_time = db.Column(db.DateTime)
    estimated_duration_minutes = db.Column(db.Integer, default=60)
    
    # Host/organizer
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    host = db.relationship('UserProfile', foreign_keys=[host_id], backref='hosted_sessions')
    
    # Relationships
    game = db.relationship('Game', backref='lobbies')
    participants = db.relationship('SessionParticipant', backref='session', cascade='all, delete-orphan')
    
    def __repr__(self):
        game_title = self.game.title if self.game else "Unknown"
        return f'<SessionLobby {self.id} - {game_title} ({self.status})>'
    
    @property
    def slots_remaining(self):
        """Calculate remaining player slots."""
        return max(0, self.slots_total - self.slots_filled) if self.slots_total else 0
    
    @property
    def can_start(self):
        """Check if session has minimum players to start."""
        return self.slots_filled >= 2
    
    @property
    def is_full(self):
        """Check if session has reached max capacity."""
        return self.slots_filled >= self.slots_total
    
    @property
    def estimated_end_time(self):
        """Calculate estimated end time based on game playtime."""
        if not self.started_at:
            return None
        duration = self.estimated_duration_minutes or 60
        return self.started_at + timedelta(minutes=duration)
    
    @property
    def time_remaining_minutes(self):
        """Get minutes remaining until estimated end."""
        if self.status != SessionStatus.ACTIVE.value or not self.estimated_end_time:
            return None
        remaining = (self.estimated_end_time - datetime.utcnow()).total_seconds() / 60
        return max(0, int(remaining))
    
    @property
    def is_overdue(self):
        """Check if session has exceeded estimated playtime."""
        if self.status != SessionStatus.ACTIVE.value or not self.estimated_end_time:
            return False
        return datetime.utcnow() > self.estimated_end_time
    
    def add_participant(self, user):
        """Add a participant to the session with validation."""
        if not user:
            raise ValueError("User cannot be None")
        
        if self.is_full:
            raise ValueError("Session is full")
        
        if any(p.user_id == user.id for p in self.participants):
            raise ValueError("User already in this session")
        
        if not user.can_join_session():
            raise ValueError("User does not meet eligibility criteria")
        
        # Check venue capacity only for active sessions
        if self.status == SessionStatus.ACTIVE.value:
            venue = VenueConfig.get_or_create()
            if not venue.can_accommodate(1):
                raise ValueError("Venue is at maximum capacity")
        
        participant = SessionParticipant(session_id=self.id, user_id=user.id)
        self.participants.append(participant)
        self.slots_filled += 1
        return participant
    
    def remove_participant(self, user):
        """Remove a participant from the session."""
        if not user:
            return False
        
        participant = SessionParticipant.query.filter_by(
            session_id=self.id, user_id=user.id
        ).first()
        
        if participant:
            self.participants.remove(participant)
            self.slots_filled = max(1, self.slots_filled - 1)
            db.session.delete(participant)
            return True
        return False
    
    def complete_session(self):
        """Mark session as completed and award credits."""
        if self.status != SessionStatus.ACTIVE.value:
            raise ValueError("Only active sessions can be completed")
        
        self.status = SessionStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()
        
        # Award credits to all participants
        for participant in self.participants:
            if not participant.user:
                continue
            
            participant.user.sessions_completed += 1
            participant.user.reliability_streak += 1
            
            reward = 10
            participant.user.credit_balance += reward
            
            transaction = CreditTransaction(
                user_id=participant.user_id,
                amount=reward,
                transaction_type='SESSION_REWARD',
                description=f'Completed session #{self.id} - {self.game.title if self.game else "Unknown"}'
            )
            db.session.add(transaction)
        
        return True


# ============================================================================
# SESSION PARTICIPANT (Junction Table)
# ============================================================================
class SessionParticipant(db.Model):
    """Junction table linking users to sessions."""
    __tablename__ = 'session_participants'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ACTIVE')
    
    __table_args__ = (
        db.UniqueConstraint('session_id', 'user_id', name='unique_participant'),
    )
    
    def __repr__(self):
        return f'<SessionParticipant user_id={self.user_id} session_id={self.session_id}>'


# ============================================================================
# CREDIT TRANSACTION (Financial Ledger)
# ============================================================================
class CreditTransaction(db.Model):
    """Audit trail for all credit movements."""
    __tablename__ = 'credit_transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<CreditTransaction user_id={self.user_id} amount={self.amount} type={self.transaction_type}>'