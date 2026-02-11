import json
import os
from datetime import datetime
from app import app
from models import db, Game, UserProfile, SessionLobby, SessionParticipant, SessionStatus, VenueConfig, CreditTransaction

def init_db():
    """Initialize database with comprehensive error handling."""
    with app.app_context():
        try:
            print("🛠️  Dropping and Recreating Tables...")
            db.drop_all()
            db.create_all()

            # ===== 1. VENUE CONFIGURATION =====
            print("🏢 Creating Venue Configuration...")
            venue = VenueConfig(
                name='TableTop Cafe #001 - Yerevan Central',
                max_capacity=20,
                max_tables=5,
                operating_hours_start=10,
                operating_hours_end=22
            )
            db.session.add(venue)
            db.session.commit()
            print(f"✓ Venue created: {venue.name} (Capacity: {venue.max_capacity})")

            # ===== 2. LOAD GAMES FROM JSON =====
            print("📚 Loading Board Games...")
            games_loaded = 0
            json_file = 'hobbygames_full_export.json'
            
            if not os.path.exists(json_file):
                print(f"⚠️  {json_file} not found. Creating fallback games...")
                raw_data = [
                    {'title': 'Catan', 'price': '25 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Catan'], 'playtime_minutes': 60},
                    {'title': 'Ticket to Ride', 'price': '30 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Ticket'], 'playtime_minutes': 90},
                    {'title': 'Pandemic', 'price': '28 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Pandemic'], 'playtime_minutes': 45},
                ]
            else:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                except json.JSONDecodeError:
                    print(f"⚠️  {json_file} is invalid JSON. Using fallback games...")
                    raw_data = [
                        {'title': 'Catan', 'price': '25 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Catan'], 'playtime_minutes': 60},
                        {'title': 'Ticket to Ride', 'price': '30 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Ticket'], 'playtime_minutes': 90},
                        {'title': 'Pandemic', 'price': '28 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Pandemic'], 'playtime_minutes': 45},
                    ]

            if not isinstance(raw_data, list):
                print("❌ Data is not a list. Aborting.")
                return

            for item in raw_data:
                try:
                    if not item.get('title'):
                        continue
                    
                    title = str(item.get('title', 'Unknown')).strip()
                    price = str(item.get('price', 'N/A')).strip()
                    gallery = item.get('gallery', [])
                    
                    # Skip if no gallery
                    if not gallery or len(gallery) == 0:
                        continue
                    
                    image_url = gallery[0] if gallery else None
                    playtime = item.get('playtime_minutes', 60)
                    
                    game = Game(
                        title=title,
                        price=price,
                        image_url=image_url,
                        estimated_playtime_minutes=playtime or 60,
                        is_available=True,
                        full_data=item
                    )
                    db.session.add(game)
                    games_loaded += 1
                    
                    if games_loaded % 50 == 0:
                        db.session.commit()
                        print(f"  → Loaded {games_loaded} games...")
                    
                    # Limit to 10 for demo
                    if games_loaded >= 10:
                        break
                
                except Exception as e:
                    print(f"  ⚠️  Skipping game: {str(e)}")
                    continue
            
            db.session.commit()
            print(f"✓ Loaded {games_loaded} games")

            # ===== 3. CREATE USERS =====
            print("👤 Creating Sample Users...")
            users = [
                UserProfile(
                    username="Anri_Admin",
                    email="admin@tabletop.local",
                    credit_balance=1000,
                    reliability_streak=10,
                    sessions_completed=25,
                    sessions_cancelled=0
                ),
                UserProfile(
                    username="Gamer_Guest",
                    email="guest@tabletop.local",
                    credit_balance=250,
                    reliability_streak=2,
                    sessions_completed=5,
                    sessions_cancelled=1
                ),
                UserProfile(
                    username="Alice_Player",
                    email="alice@tabletop.local",
                    credit_balance=100,
                    reliability_streak=3,
                    sessions_completed=8,
                    sessions_cancelled=0
                ),
                UserProfile(
                    username="Bob_Host",
                    email="bob@tabletop.local",
                    credit_balance=500,
                    reliability_streak=7,
                    sessions_completed=15,
                    sessions_cancelled=0
                )
            ]
            
            db.session.add_all(users)
            db.session.commit()
            print(f"✓ Created {len(users)} users")

            # ===== 4. CREATE SAMPLE SESSIONS =====
            print("🎲 Creating Sample Sessions...")
            game1 = Game.query.first()
            game2 = Game.query.order_by(Game.id.desc()).first()
            
            admin_user = UserProfile.query.filter_by(username='Anri_Admin').first()
            guest_user = UserProfile.query.filter_by(username='Gamer_Guest').first()
            alice_user = UserProfile.query.filter_by(username='Alice_Player').first()
            bob_user = UserProfile.query.filter_by(username='Bob_Host').first()

            if all([game1, game2, admin_user, guest_user, alice_user, bob_user]):
                # RECRUITING session
                recruiting_session = SessionLobby(
                    game_id=game1.id,
                    host_id=admin_user.id,
                    slots_total=4,
                    slots_filled=2,
                    status=SessionStatus.RECRUITING.value,
                    estimated_duration_minutes=game1.estimated_playtime_minutes or 60
                )
                db.session.add(recruiting_session)
                db.session.flush()

                recruiting_participant = SessionParticipant(
                    session_id=recruiting_session.id,
                    user_id=guest_user.id,
                    status='ACTIVE'
                )
                db.session.add(recruiting_participant)

                # ACTIVE session
                active_session = SessionLobby(
                    game_id=game2.id,
                    host_id=bob_user.id,
                    table_number=1,
                    slots_total=3,
                    slots_filled=3,
                    status=SessionStatus.ACTIVE.value,
                    started_at=datetime.utcnow(),
                    estimated_duration_minutes=game2.estimated_playtime_minutes or 60
                )
                db.session.add(active_session)
                db.session.flush()

                active_participants = [
                    SessionParticipant(
                        session_id=active_session.id,
                        user_id=alice_user.id,
                        status='ACTIVE'
                    ),
                    SessionParticipant(
                        session_id=active_session.id,
                        user_id=guest_user.id,
                        status='ACTIVE'
                    )
                ]
                db.session.add_all(active_participants)
                
                if game2:
                    game2.is_available = False

                db.session.commit()
                print(f"✓ Created 2 sample sessions")
            else:
                print("⚠️  Skipping sessions: Missing games or users")

            # ===== 5. CREATE SAMPLE TRANSACTIONS =====
            print("💰 Creating Sample Transactions...")
            admin_user = UserProfile.query.filter_by(username='Anri_Admin').first()
            
            if admin_user:
                transactions = [
                    CreditTransaction(
                        user_id=admin_user.id,
                        amount=10,
                        transaction_type='SESSION_REWARD',
                        description='Completed session: Catan'
                    ),
                    CreditTransaction(
                        user_id=admin_user.id,
                        amount=5,
                        transaction_type='RELIABILITY_BONUS',
                        description='Maintained 10-session streak'
                    )
                ]
                db.session.add_all(transactions)
                db.session.commit()
                print(f"✓ Created {len(transactions)} sample transactions")

            print("\n✅ Database successfully initialized!")

        except Exception as e:
            print(f"❌ Critical error: {str(e)}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    init_db()