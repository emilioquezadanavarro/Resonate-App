"""
setup_db.py

A standalone script to initialize the project database.

It performs two main actions:
1. Creates the 'resonate.db' file and all tables defined in app/database.py.
2. Seeds the 'moods' table with default values (Happy, Sad, etc.) if empty.

Usage: Run manually via terminal: `python setup_db.py`

"""

from app import create_app
from app.database import db, Mood

# Create app instance
app = create_app()

def setup():
    # Enter the context (activates the config)
    try:
        with app.app_context():
            print("Creating all database tables 🛠️ ...")
            db.create_all()
            print("Tables created ✅ !")

            # Seed Moods (only if empty)
            if Mood.query.count() == 0:
                print("Seeding initial moods 🌱 ...")
                moods = ["Happy", "Sad", "Energetic", "Calm", "Anxious", "Focused", "Melancholic", "Excited"]
                for label in moods:
                    db.session.add(Mood(label=label))
                db.session.commit()
                print(f"✨ Added {len(moods)} moods.")
            else: # Make the script Idempotent
                print("Moods already exist. Skipping seed 👌.")

    except Exception as e:

        print(f"ERROR: Failed to create database tables. Reason: {e}")

if __name__ == "__main__":
    setup()