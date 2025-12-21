"""
app/database.py

Defines the SQL database schema (ORM Models) for Resonate.

This file handles the translation between Python Classes and SQLite tables.

Key Models:
- User: Stores profile info and AI personalization factors (Age/Gender).
- JournalEntry: The core content (Text) + AI metadata (Music Query).
- Mood: A static list of emotions (Happy, Sad, etc.) for tagging entries.
- Song: Music metadata + Vector Embeddings (stored as JSON text).
- Recommendation: Logs the match between an Entry and a Song.

Dependencies: Flask-SQLAlchemy, JSON (for vector storage).

"""
# Import and create a db object:
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import json


# Initialize the db object without passing the app instance yet (we will link it to the app later in __init__.py)
db = SQLAlchemy()

# 1. Association Table (Many-to-Many)

# This links JournalEntry <-> Mood
entry_moods = db.Table('entry_moods',
    db.Column('journal_entry_id', db.Integer, db.ForeignKey('journal_entries.id'), primary_key=True),
    db.Column('mood_id', db.Integer, db.ForeignKey('moods.id'), primary_key=True)
)

# 2. The Models

class User(db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(20), nullable=False)  # Used for AI tone
    age = db.Column(db.Integer, nullable=False)  # Used for AI references
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now()) # Auto-handling timestamps

    # A user has many journal entries
    entries = db.relationship('JournalEntry', backref='user', lazy=True)

    # A helper method for debugging
    def __repr__(self):
        return f'<User {self.username}>'


class Mood(db.Model):

    """
    This is the "target" of the Many-to-Many relationship

    """

    __tablename__ = 'moods'

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), unique=True, nullable=False)


class JournalEntry(db.Model):

    __tablename__ = 'journal_entries'

    id = db.Column(db.Integer, primary_key=True)

    # Link Journal entry to User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    content = db.Column(db.Text, nullable=False)
    ai_summary = db.Column(db.Text, nullable=True)
    music_query = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # M2M relationship to moods
    moods = db.relationship('Mood', secondary=entry_moods, backref='entries')


class Song(db.Model):

    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    lyrics = db.Column(db.Text, nullable=False)

    # SPECIAL HANDLING: The Embedding
    # We store it as a Text block, but we treat it as JSON.

    lyrics_embedding = db.Column(db.Text)

    # Helper method to get the vector back as a list
    def get_embedding(self):
        if self.lyrics_embedding:
            return json.loads(self.lyrics_embedding)
        return []


class Recommendation(db.Model):

    """
    # This acts as a log of what the AI gave the user
    # It needs ForeignKeys to both JournalEntry and Song

    """

    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    ai_explanation = db.Column(db.Text, nullable=True)
    is_like = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
