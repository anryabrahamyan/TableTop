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
            try:
                venue = VenueConfig(
                    name='TableTop Cafe #001 - Yerevan Central',
                    max_capacity=20,
                    max_tables=5,
                    operating_hours_start=10,
                    operating_hours_end=22
                )
                db.session.add(venue)
                db.session.flush()
                print(f"✓ Venue created: {venue.name} (Capacity: {venue.max_capacity})")
            except Exception as e:
                print(f"⚠️  Error creating venue config: {str(e)}")
                db.session.rollback()
                return

            # ===== 2. IMPORT RICH DATA FROM JSON =====
            print("📚 Importing Board Game Metadata from JSON...")
            games_loaded = 0
            try:
                json_file = 'hobbygames_full_export.json'
                if not os.path.exists(json_file):
                    print(f"⚠️  Warning: {json_file} not found. Creating test games instead.")
                json_file = 'hobbygames_full_export.json'
                if not os.path.exists(json_file):
                    print(f"⚠️  Warning: {json_file} not found. Creating test games instead.")
                    raw_data = [
                        {'title': 'Catan', 'price': '25 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Catan'], 'playtime_minutes': 60},
                        {'title': 'Ticket to Ride', 'price': '30 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Ticket+to+Ride'], 'playtime_minutes': 90},
                        {'title': 'Pandemic', 'price': '28 AMD', 'gallery': ['https://via.placeholder.com/300x300?text=Pandemic'], 'playtime_minutes': 45}
                    ]
                else:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                
                if not isinstance(raw_data, list):
                    print("❌ Error: JSON file is not a list of games")
                    db.session.rollback()
                    return

                for item in raw_data:
                    try:
                        # Validate required fields
                        if not item.get('title'):
                            continue
                        
                        # Skip accessories and non-games
                        if "Протекторы" in item.get('title', ''):
                            continue
                        
                        gallery = item.get('gallery', [])
                        if not gallery or len(gallery) == 0:
                            continue

                        new_game = Game(
                            title=item['title'].strip(),
                            price=str(item.get('price', 'N/A')).strip(),
                            image_url=gallery[0] if gallery else None,
                            estimated_playtime_minutes=item.get('playtime_minutes', 60),
                            full_data=item,
                            is_available=True
                        )
                        db.session.add(new_game)
                        games_loaded += 1

                        # Commit in batches to avoid memory issues
                        if games_loaded % 50 == 0:
                            db.session.commit()
                            print(f"  → Loaded {games_loaded} games...")

                        # Limit to 30 games for initial seed
                        if games_loaded >= 30:
                            break

                    except Exception as e:
                        print(f"  ⚠️  Skipping game: {str(e)}")
                        db.session.rollback()
                        continue

                db.session.commit()
                print(f"✓ Imported {games_loaded} games")

            except FileNotFoundError:
                print("❌ Error: hobbygames_full_export.json not found!")
                print("   Please ensure the file exists in the project root directory.")
                db.session.rollback()
                return
            except json.JSONDecodeError:
                print("❌ Error: hobbygames_full_export.json is not valid JSON")
                db.session.rollback()
                return
            except Exception as e:
                print(f"❌ Unexpected error loading games: {str(e)}")
                db.session.rollback()
                return

            # ===== 3. CREATE SYSTEM USERS =====
            print("👤 Creating Sample Users...")
            try:
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
                db.session.flush()
                print(f"✓ Created {len(users)} users")

            except Exception as e:
                print(f"❌ Error creating users: {str(e)}")
                db.session.rollback()
                return

            # ===== 4. CREATE SAMPLE SESSIONS =====
            print("🎲 Creating Sample Sessions...")
            try:
                # Get sample games and users
                game1 = Game.query.first()
                if not game1:
                    print("⚠️  No games available to create sessions")
                    db.session.rollback()
                    return
                
                game2 = Game.query.order_by(Game.id.desc()).limit(1).first()
                
                admin_user = UserProfile.query.filter_by(username='Anri_Admin').first()
                guest_user = UserProfile.query.filter_by(username='Gamer_Guest').first()
                alice_user = UserProfile.query.filter_by(username='Alice_Player').first()
                bob_user = UserProfile.query.filter_by(username='Bob_Host').first()

                if not all([game1, admin_user, guest_user, alice_user, bob_user]):
                    print("⚠️  Skipping sessions: Missing games or users")
                else:
                    # Create a RECRUITING session
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

                    # Add participants to recruiting session
                    recruiting_participant = SessionParticipant(
                        session_id=recruiting_session.id,
                        user_id=guest_user.id,
                        status='ACTIVE'
                    )
                    db.session.add(recruiting_participant)

                    # Create an ACTIVE session
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

                    # Add participants to active session
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

                    # Mark active game as unavailable
                    if game2:
                        game2.is_available = False

                    db.session.commit()
                    print(f"✓ Created 2 sample sessions (1 recruiting, 1 active)")

            except Exception as e:
                print(f"❌ Error creating sessions: {str(e)}")
                db.session.rollback()
                return

            # ===== 5. CREATE SAMPLE TRANSACTIONS =====
            print("💰 Creating Sample Transactions...")
            try:
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

            except Exception as e:
                print(f"❌ Error creating transactions: {str(e)}")
                db.session.rollback()
                return

            print("\n✅ Database successfully initialized!")
            print(f"   - {games_loaded} games loaded")
            print(f"   - {len(users)} users created")
            print(f"   - Venue configured with {venue.max_capacity} player capacity")

        except Exception as e:
            print(f"❌ Critical error during database initialization: {str(e)}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    init_db()