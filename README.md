# Resonate 🌿

**Your AI-powered journaling companion.**

---

## Features

- **Distraction-free writing** — A clean, minimalist interface for capturing your thoughts without clutter.
- **Mood tracking** — Tag entries with emotions using our Emerald green and pastel chip UI. Select multiple moods per entry to capture how you're really feeling.
- **AI Insights** — Each entry gets an empathetic analysis and personalized **music curation** powered by AI. Discover songs that match your vibe.
- **Chat with Camus** — A floating chat assistant that reflects on your journal history, recommends books, and answers questions using your own words.
- **Safety routing** — Dedicated crisis and toxic content detection. Entries flagged for self-harm or hate speech are routed to supportive resources or blocked—never saved—keeping Resonate a safe space for reflection.

---

## Tech Stack

- **Backend:** Flask
- **Frontend:** Alpine.js, Tailwind CSS, DaisyUI
- **Database:** SQLite (Flask-SQLAlchemy) + ChromaDB (vector embeddings for journal memory search)
- **AI Integration:** OpenAI (summaries, security, embeddings), Google Gemini (music recommendations), Tavily (web search for chat)

---

## Project Structure

```
Resonate-App/
├── app/
│   ├── __init__.py                           # Flask app factory, db init, blueprint registration
│   ├── database.py                           # SQLAlchemy models (User, JournalEntry, Mood, Song, Recommendation)
│   ├── routes.py                             # All Flask routes (profile, journal, chat, crisis/toxic redirects)
│   ├── services/                             # Business logic & AI agents
│   │   ├── ai_chatbox_agent.py               # Chat bot (LangChain + Tavily web search)
│   │   ├── ai_entry_summary_agent.py         # Empathetic journal analysis (OpenAI)
│   │   ├── ai_library_agent.py               # Book recommendations
│   │   ├── ai_music_recommendation_agent.py  # Music curation (Google Gemini)
│   │   ├── ai_security_agent.py              # Content safety classifier (OpenAI) — crisis/toxic detection
│   │   ├── ai_judge_agent.py                 # Quality validation for recommendations
│   │   ├── journal_services.py               # Journal CRUD, entry creation flow
│   │   ├── past_recommendation_service.py    # Anti-repetition, recommendation history
│   │   ├── user_service.py                   # User CRUD
│   │   ├── vector_engine.py                  # ChromaDB embeddings for journal memory search
│   │   └── tools.py                          # LangChain tools (search_journal_memory, consult_librarian)
│   └── templates/                            # Jinja2 + Tailwind + DaisyUI
│       ├── layout.html                       # Master layout, navbar, chat bubble, footer
│       ├── index.html                        # Login / profile selector
│       ├── create_profile.html               # Onboarding form
│       ├── profile.html                      # Dashboard, journal history, "Write Entry" CTA
│       ├── journal.html                      # New entry form, mood chips, textarea
│       ├── edit_entry.html                   # Edit existing entry
│       ├── entry_detail.html                 # View entry, AI insights, music card
│       ├── crisis.html                       # Safety page — crisis resources (no nav links)
│       └── toxic.html                        # Safety page — content blocked (no nav links)
├── run.py                                    # Entry point, dev server
├── setup_db.py                               # DB init, seed moods
├── requirements.txt
├── .env                                      # API keys (not in repo)
└── chroma_db/                                # ChromaDB vector store (created at runtime)
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Resonate-App.git
cd Resonate-App
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

Create a `.env` file in the project root with your API keys:

```
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
LANGFUSE_SECRET_KEY=your_langfuse_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
```

### 5. Initialize the database

```bash
python setup_db.py
```

### 6. Run the app

```bash
python run.py
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/) in your browser.

---

## Deployment (Render)

The app includes `gunicorn` for production. Use a start command such as:

```bash
gunicorn -w 4 -b 0.0.0.0:$PORT "run:app"
```

Ensure your Render service is configured to run this command and that all required environment variables are set in the Render dashboard.
