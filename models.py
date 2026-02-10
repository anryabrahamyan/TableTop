from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

db = SQLAlchemy()

# 1. INTERNAL GAME REGISTRY (FR.1.2)
class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(50))
    image_url = db.Column(db.String(512))
    is_available = db.Column(db.Boolean, default=True) # Staff Toggle support
    
    # Store the entire HobbyGames JSON object (NoSQL style)
    full_data = db.Column(JSONB) 

# 2. USER IDENTITY & CREDIT ENGINE (FR.1.1 & FR.4.1)
class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Identity (FR.1.1)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # Financial Ledger (FR.4.1)
    # This stores the "TableTop Credits" used for the peer-to-peer marketplace.
    credit_balance = db.Column(db.Integer, default=0)
    
    # Social Metadata (URD: Gamer Experience)
    # Tracks how often the user shows up to joined sessions without "ghosting".
    reliability_streak = db.Column(db.Integer, default=0)
    
    # Play History (URD: Digital Trophy Case)
    # We can use this to show what games the user has played at the cafe.
    bio = db.Column(db.Text, nullable=True)
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<UserProfile {self.username}>'

# 3. SESSION & LFG LOGIC (FR.2.1)
class SessionLobby(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    table_number = db.Column(db.Integer)
    status = db.Column(db.String(20), default='RECRUITING') # RECRUITING, ACTIVE, COMPLETED
    slots_total = db.Column(db.Integer)
    slots_filled = db.Column(db.Integer, default=1)
    
    # Relationship to easily get game info from a lobby (e.g., session.game.title)
    game = db.relationship('Game', backref='lobbies')