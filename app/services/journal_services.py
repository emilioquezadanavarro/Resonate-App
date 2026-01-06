from app.database import db, JournalEntry

class JournalEntryService:
    @staticmethod
    def get_entries_by_user(user_id):
        return JournalEntry.query.filter_by(user_id=user_id).order_by(JournalEntry.created_at.desc()).all()
