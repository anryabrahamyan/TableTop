This README provides a comprehensive overview of the TableTop project in its current functional state. It is designed to give another model (or developer) a clear understanding of the architecture, data structures, and features implemented so far.

🎲 TableTop: Cafe Management System
TableTop is a specialized social operating system for board game cafes. It digitizes the "Live Shelf" and "Table Map" to solve the logistical hurdles of finding players (LFG) and managing physical game inventory.

🏗️ Technical Architecture
The system is built as a Modular Monolith using the following stack:

Backend: Flask (Python)

Database: PostgreSQL (with JSONB support for NoSQL-style game metadata)

ORM: SQLAlchemy

Data Source: Custom surgical scraper (BeautifulSoup4/lxml) for HobbyGames.ru

Frontend: Jinja2 Templates with a "Parchment & Wood" board game aesthetic.

📊 Data Models (The Core Logic)
The database schema is designed to manage physical resources as digital states:

Game: The internal registry. Stores high-fidelity metadata (titles, prices, images) and a full_data JSONB field containing the complete scraped export (descriptions, package contents, gallery).

UserProfile: Tracks user identity, Credit Balance (for the circular economy), and Reliability Streaks (to discourage "ghosting" sessions).

SessionLobby: A state machine for the cafe floor. Tracks which game is at which table and manages transitions between RECRUITING (LFG) and ACTIVE (In-play).

📂 File Manifest
app.py: Main application entry point with routing for the Dashboard, Library, and Game Details.

models.py: Declarative SQLAlchemy models defining the relational structure.

database.py: Utility script to initialize the Postgres schema and seed it with rich data from the JSON export.

fetch_data.py: A surgical scraper that pulls hundreds of board game entries from external sources.

hobbygames_full_export.json: The raw data payload used to populate the internal registry.

static/css/style.css: A custom theme utilizing a board-game-inspired "parchment" color palette.

templates/:

base.html: Persistent layout with the "Operator" navigation bar.

dashboard.html: The "Cafe Floor Overview" showing active and recruiting sessions.

library.html: The "Shelf-to-App Sync" interface for staff to toggle game availability.

game_details.html: A rich view displaying NoSQL metadata, galleries, and component lists.

🚀 Current Implementation Progress
1. Internal Game Registry (FR.1.2)

We have moved away from third-party API dependency. We now host our own curated catalog of ~30 games (initially seeded) with high-definition imagery and package details stored in JSONB.

2. Shelf-to-App Sync (FR.3.1)

Staff can currently toggle the is_available status of any game in the library. This status is reflected globally, ensuring users only see games actually sitting on the shelf.

3. Floor Awareness (UR.Admin)

The Dashboard provides a split view of the cafe:

Recruiting Lobbies: Open seats for gamers looking for a group.

Active Tables: Physical tables currently occupied by a specific session.

4. Credit Engine Infrastructure (FR.4.1)

The UserProfile model is ready to support the circular economy. Users are initialized with credit balances, providing the foundation for the peer-to-peer marketplace.

🛠️ Environment Setup
Database (Docker):

Bash
docker run --name tabletop-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=tabletop_db \
  -p 5432:5432 \
  -d postgres
Environment Variables (.env):

Plaintext
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tabletop_db
Seeding the System:

Bash
python3 database.py