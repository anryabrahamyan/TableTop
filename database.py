import json
from app import app
from models import db, Game, UserProfile, SessionLobby

def init_db():
    with app.app_context():
        print("🛠️  Dropping and Recreating Tables...")
        db.drop_all()
        db.create_all()

        # --- 1. IMPORT RICH DATA FROM JSON (The Internal Registry) ---
        print("📚 Importing Board Game Metadata from JSON...")
        try:
            with open('hobbygames_full_export.json', 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                
                # We filter out items that don't have a gallery or are just accessories
                # to keep the "Library" looking high-quality
                count = 0
                for item in raw_data:
                    if not item.get('gallery') or "Протекторы" in item['title']:
                        continue
                    
                    new_game = Game(
                        title=item['title'],
                        price=item.get('price', 'N/A'),
                        image_url=item['gallery'][0], # Main Image
                        full_data=item,              # All NoSQL-style metadata
                        is_available=True
                    )
                    db.session.add(new_game)
                    count += 1
                    if count >= 30: break # Limit to 30 games for the initial seed
        except FileNotFoundError:
            print("❌ Error: hobbygames_full_export.json not found!")

        # --- 2. CREATE SYSTEM USERS (The Credit Engine) ---
        print("👤 Creating Sample Users...")
        # A staff member and a regular gamer
        users = [
            UserProfile(username="Anri_Admin", credit_balance=1000, reliability_streak=10),
            UserProfile(username="Gamer_Guest", credit_balance=250, reliability_streak=2)
        ]
        db.session.add_all(users)
        db.session.flush() # Flush to get IDs for the next step

        # --- 3. CREATE ACTIVE LOBBIES (The LFG Engine) ---
        print("🎲 Creating Active Cafe Sessions...")
        # Let's put one game into an 'ACTIVE' state at a table
        active_game = Game.query.filter(Game.title.contains("Квиксо")).first()
        if active_game:
            lobby = SessionLobby(
                game_id=active_game.id,
                table_number=5,
                status='ACTIVE',
                slots_total=4,
                slots_filled=3
            )
            db.session.add(lobby)
            active_game.is_available = False # Mark as checked out

        db.session.commit()
        print("✅ Success! Cafe System is fully seeded.")

if __name__ == "__main__":
    init_db()