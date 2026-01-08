from app.database import db, JournalEntry, Mood

class JournalEntryService:
    @staticmethod
    def get_entries_by_user(user_id):
        return JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.created_at.desc()).all()

    @staticmethod
    def create_entry(user_id, content, mood_ids):

        try:

            # Create the new entry object
            new_entry = JournalEntry(user_id=user_id, content=content)

            # Link the Moods - Loop through the list of mood_ids
            # For each ID, fetch the Mood object from the DB and then append it to new_entry.moods
            if mood_ids:
                for mood_id in mood_ids:
                    mood = Mood.query.get(mood_id)
                    if mood:
                        new_entry.moods.append(mood)

            # Add entry to DB
            db.session.add(new_entry)

            # Commit to DB
            db.session.commit()

            return new_entry

        except Exception as e:
            print(f"Service Error: {e} ❌")
            db.session.rollback()
            return None

