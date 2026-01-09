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

    @staticmethod
    def get_entry_by_id(entry_id):
        return JournalEntry.query.get(entry_id)

    @staticmethod
    def update_entry_by_id(entry_id, new_content):

        try:

            entry_to_update = JournalEntry.query.get(entry_id)

            if entry_to_update:

                entry_to_update.content = new_content

                db.session.commit()

                return entry_to_update

            return None

        except Exception as e:
            print(f"Service Error: {e} ❌")
            db.session.rollback()
            return None

    @staticmethod
    def delete_entry_by_id(entry_id):

        try:

            entry_to_delete = JournalEntry.query.get(entry_id)

            if entry_to_delete:

                db.session.delete(entry_to_delete)
                db.session.commit()

                return True

            return None

        except Exception as e:
            print(f"Service Error: {e} ❌")
            db.session.rollback()
            return None