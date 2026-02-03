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

            # Add entry to DB
            db.session.add(new_entry)

            # Fetch and Attach Moods
            if mood_ids:
                # We fetch the actual Mood objects from the DB
                moods = Mood.query.filter(Mood.id.in_(mood_ids)).all()
                # We assign them. Since new_entry is in the session, this works perfectly.
                new_entry.moods = moods

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
    def update_entry_by_id(entry_id, new_content, mood_ids=None):

        try:

            entry_to_update = JournalEntry.query.get(entry_id)

            if entry_to_update:

                # Update Content
                entry_to_update.content = new_content

                # Update Moods (If provided)
                if mood_ids is not None:
                    # Clear existing moods first
                    entry_to_update.moods = []

                    # Add the new selection
                    for m_id in mood_ids:
                        mood = Mood.query.get(m_id)
                        if mood:
                            entry_to_update.moods.append(mood)

                # Deleting the old summary and music query so user can click "Analyze" again.
                entry_to_update.ai_summary = None
                entry_to_update.music_query = None

                # Commit to DB
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