from app.database import db, Recommendation

class PastRecommendationService:
    @staticmethod
    def get_recent_recommendations(user_id, item_type, limit=50):
        """
        THE HISTORY CHECKER

        Fetches a list of titles (strings) that a specific user has already seen.

        """
        # Query the database
        recent_items = (
            db.session.query(Recommendation.title)
            .filter(Recommendation.user_id == user_id)
            .filter(Recommendation.type == item_type)
            .order_by(Recommendation.created_at.desc())
            .limit(limit)
            .all()
        )

        blacklist = []

        for item in recent_items:
            blacklist.append(item[0])

        return blacklist

    @staticmethod
    def save_recommendations(user_id, items, item_type, journal_id=None):
        """
        THE HISTORY RECORDER
        Logs a list of new AI suggestions into the database.

        Args:
            user_id: The user ID.
            journal_id (int): The entry ID.
            items (list): The list of songs/books to save.
            item_type (str): MUST be specified (e.g. "song", "book").

        """

        try:
            for item in items:
                new_rec = Recommendation(
                    user_id=user_id,  # <--- Saving the User ID
                    journal_id=journal_id,  # <--- Can be None now
                    title=item.get('title'),
                    creator=item.get('artist') or item.get('author'),
                    type=item_type
                )
                db.session.add(new_rec)

            # Save everything
            db.session.commit()
            print(f"✅ Saved {len(items)} new {item_type} recommendations to history.")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Error saving recommendations: {e}")
            return False





