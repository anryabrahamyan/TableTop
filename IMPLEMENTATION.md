# TableTop Project - Implementation Guide

## Overview

This project implements a TableTop cafe management system with four core features:

1. **LFG (Looking For Group) Session Management** - Create and join gaming sessions
2. **Credit System** - Track credits for participation with rewards and penalties
3. **User Profiles** - User authentication and profile management
4. **Testing & Error Handling** - Comprehensive test suite with edge case coverage

## Project Structure

```
├── app.py                 # Flask application with all routes
├── models.py              # SQLAlchemy ORM models and business logic
├── database.py            # Database initialization utilities
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (DATABASE_URL, SECRET_KEY)
├── test_models.py         # Unit tests for models
├── test_integration.py    # Integration tests for HTTP endpoints
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── profile.html
│   ├── credits.html
│   ├── create_session.html
│   ├── view_session.html
│   └── error.html
├── static/                # CSS and static files
│   └── css/
│       └── style.css
└── myenv/                 # Python virtual environment
```

## Setup Instructions

### 1. Activate Virtual Environment

```bash
cd tabletop-project
source myenv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Database

Create/edit `.env` file with:

```bash
# For SQLite (development):
DATABASE_URL=sqlite:///tabletop.db

# For PostgreSQL (production):
DATABASE_URL=postgresql://user:password@localhost:5432/tabletop

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 4. Initialize Database

```bash
python database.py
```

## Running the Application

### Development Server

```bash
python app.py
```

The application will run at `http://localhost:5000`

### Running Tests

```bash
# Run all unit tests
pytest test_models.py -v

# Run all integration tests
pytest test_integration.py -v

# Run all tests with coverage
pytest test_models.py test_integration.py -v

# Run specific test class
pytest test_models.py::TestUserProfile -v
```

Or use the provided test script:

```bash
bash run_tests.sh
```

## Feature Documentation

### 1. LFG Session Management

**Models:**
- `SessionLobby` - Represents a gaming session/table
- `SessionParticipant` - Junction table linking users to sessions
- `SessionStatus` - Enum for session states (RECRUITING, ACTIVE, COMPLETED, CANCELLED)

**Routes:**
- `POST /session/create` - Host creates a new session
- `POST /session/<id>/join` - Player joins a session
- `POST /session/<id>/leave` - Player leaves a session
- `POST /session/<id>/start` - Host starts the session
- `POST /session/<id>/complete` - Host marks session as complete (awards credits)
- `POST /session/<id>/cancel` - Cancel a session

**Validation:**
- Session must have 2-10 slots
- Players cannot join full sessions
- Players cannot join if already in session
- Only host can start/complete/cancel
- Session must have minimum 2 players to start
- Only users with credit_balance > -50 can join

### 2. Credit System

**Models:**
- `CreditTransaction` - Audit trail for all credit movements
- `UserProfile.credit_balance` - Current credit amount

**Key Business Rules:**
- Users start with 0 credits
- Session participation reward: +10 credits
- Session cancellation penalty: -5 credits
- Eligibility requirement: credit_balance > -50 (users at or below -50 cannot join)
- Reliability streak: Increments on completion, resets on cancellation

**Routes:**
- `GET /credits` - View credit system dashboard and transaction history
- `GET /api/user/<id>` - JSON endpoint with credit information

**Transactions:**
- SESSION_REWARD: +10 credits when session completes
- SESSION_PENALTY: -5 credits when session cancelled
- MANUAL_ADJUSTMENT: Admin adjustments

### 3. User Profiles

**Models:**
- `UserProfile` - User identity and statistics

**Key Fields:**
- `username` - Unique identifier (auto-created on first login)
- `credit_balance` - Current credits
- `reliability_streak` - Consecutive completed sessions
- `sessions_completed` - Total completed sessions
- `sessions_cancelled` - Total cancelled sessions

**Routes:**
- `GET /login` - Login form
- `POST /login` - Authenticate user (creates if doesn't exist)
- `GET /profile/<user_id>` - View user profile with statistics
- `GET /dashboard` - User dashboard with sessions list

**Features:**
- Simplified login (no passwords - change this for production!)
- Profile page shows:
  - Credit balance
  - Reliability streak
  - Session history
  - Credit transaction ledger

### 4. Testing & Error Handling

**Test Coverage:**

**Unit Tests (test_models.py):**
- UserProfile: 7 tests
  - User creation and uniqueness
  - Eligibility criteria (-50 boundary conditions)
  - Session joining restrictions
- Game: 2 tests
  - Game creation
  - Availability toggling
- SessionLobby: 10 tests
  - Session creation and properties
  - Participant management (add/remove)
  - Session start conditions
  - Credit awarding on completion
  - Full session rejection
- CreditTransaction: 1 test
  - Transaction audit trail

**Integration Tests (test_integration.py):**
- 26 HTTP endpoint tests covering:
  - Login and user creation
  - Dashboard and library views
  - Session CRUD operations
  - Session joining with validation
  - Credit system operations
  - Profile page rendering
- 4 validation edge case tests:
  - Username length validation
  - Game ID validation
  - Slot range (2-10) validation
  - Negative balance restrictions

**Error Handling:**
- Route-level validation with user feedback (flash messages)
- Database operation try-catch blocks
- HTTP error handlers (404, 500, 403)
- User authentication decorator (`@require_user`)
- Model-level business logic validation (no duplicate joins, full session checks, etc.)
- Graceful error pages with error codes

**Edge Cases Handled:**
1. User joins session but becomes ineligible while session recruiting
2. Session reaches capacity after user joins
3. User tries to join while already in session
4. Session complete when no participants
5. Credit balance drops below threshold between join and start
6. Duplicate join attempts
7. Non-existent game/session/user requests
8. Host tries to join own session

## Database Schema

### Games Table
```
id (PK)
title
price
image_url
is_available
full_data (JSONB)
created_at
```

### Users Table
```
id (PK)
username (UNIQUE)
email (UNIQUE)
credit_balance
reliability_streak
sessions_completed
sessions_cancelled
created_at
last_active
```

### Sessions Table
```
id (PK)
game_id (FK)
host_id (FK -> users)
status
slots_total
slots_filled
created_at
started_at
completed_at
estimated_duration_minutes
```

### Session Participants Table (Junction)
```
id (PK)
session_id (FK)
user_id (FK)
joined_at
status
```

### Credit Transactions Table
```
id (PK)
user_id (FK)
amount
transaction_type
description
created_at
```

## Environment Variables

Required in `.env`:

```bash
# Database (required)
DATABASE_URL=sqlite:///tabletop.db
# or
DATABASE_URL=postgresql://user:password@host:5432/database

# Flask (optional)
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
```

## API Endpoints

### Authentication
- `GET/POST /login` - User login/creation

### Dashboards
- `GET /dashboard` - User dashboard with sessions
- `GET /library` - Browse available games
- `GET /game_details/<id>` - Game details

### Sessions (LFG)
- `GET /session/create` - Session creation form
- `POST /session/create` - Create new session
- `GET /session/<id>` - View session details
- `POST /session/<id>/join` - Join session
- `POST /session/<id>/leave` - Leave session
- `POST /session/<id>/start` - Start session
- `POST /session/<id>/complete` - Complete session (awards credits)
- `POST /session/<id>/cancel` - Cancel session

### Credits & Profile
- `GET /profile/<user_id>` - View user profile
- `GET /credits` - Credit system dashboard
- `GET /api/sessions` - JSON: All sessions
- `GET /api/user/<id>` - JSON: User information

### Admin
- `GET /toggle_game/<game_id>` - Toggle game availability

### Error Handlers
- `404` - Not found
- `500` - Server error
- `403` - Forbidden/Unauthorized

## Implementation Highlights

### Model Business Logic
- **SessionLobby.add_participant()**: Validates eligibility, prevents duplicates, checks capacity
- **SessionLobby.complete_session()**: Awards credits, updates streaks, logs transactions
- **UserProfile.can_join_session()**: Enforces -50 balance threshold

### Route Design
- **@require_user decorator**: Enforces authentication on protected routes
- **Flash messages**: User feedback for all operations
- **Error handling**: Try-catch blocks around all DB operations
- **Validation**: Game/session existence, slot bounds, balance checks

### Testing Strategy
- **Unit tests**: Test models in isolation with in-memory SQLite
- **Integration tests**: Test full HTTP flows
- **Edge case coverage**: Boundary conditions, concurrent access, invalid states

## Common Tasks

### Add a New Game

```python
from models import db, Game
game = Game(title='Ticket to Ride', price='$40', is_available=True)
db.session.add(game)
db.session.commit()
```

### Create a User

```python
from models import db, UserProfile
user = UserProfile(username='player1')
db.session.add(user)
db.session.commit()
```

### Create a Session

```python
from models import db, SessionLobby
session = SessionLobby(game_id=1, host_id=1, slots_total=4)
db.session.add(session)
db.session.commit()
```

### Award Credits

```python
from models import UserProfile, CreditTransaction, db
user = UserProfile.query.get(1)
user.credit_balance += 10
transaction = CreditTransaction(
    user_id=user.id,
    amount=10,
    transaction_type='BONUS',
    description='Bonus credits'
)
db.session.add(transaction)
db.session.commit()
```

## Troubleshooting

### DATABASE_URL Error
If you get "Either 'SQLALCHEMY_DATABASE_URI' or 'SQLALCHEMY_BINDS' must be set":
- Ensure `.env` file exists with `DATABASE_URL` set
- Or run with: `DATABASE_URL=sqlite:///:memory: python app.py`

### Tests Fail
- Ensure pytest is installed: `pip install pytest`
- Set DATABASE_URL: `export DATABASE_URL=sqlite:///:memory:`
- Run from project root: `cd tabletop-project`

### Port Already in Use
If port 5000 is taken:
- Change in app.py: `app.run(debug=True, port=5001)`
- Or kill process: `lsof -i :5000` and `kill -9 <PID>`

## Production Deployment

1. **Use PostgreSQL** instead of SQLite
   ```bash
   DATABASE_URL=postgresql://user:password@host/dbname
   ```

2. **Use proper authentication** (currently simplified - no passwords)
   - Implement password hashing with werkzeug.security
   - Add session management

3. **Use environment secrets**
   - Never commit `.env` to version control
   - Use production secret key
   - Enable HTTPS

4. **Database migrations**
   - Use Flask-Migrate for schema changes
   - Test migrations before deployment

5. **Error monitoring**
   - Integrate Sentry or similar
   - Set up logging
   - Monitor performance

## Support & Next Steps

- Review README.md for system architecture
- Check test files for usage examples
- Inspect templates/ for UI implementation
- Review app.py routes for available endpoints
