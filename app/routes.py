from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from .database import db, User, Mood
from app.services.user_service import UserService
from app.services.journal_services import JournalEntryService
from app.services.ai_entry_summary_agent import SummaryAgent
from app.services.ai_music_recommendation_agent import MusicRecommendationAgent
from app.services.vector_engine import vector_engine
from app.services.ai_chatbox_agent import chatbox_agent
from app.services.past_recommendation_service import PastRecommendationService

# Create the Blueprint object
main = Blueprint('main', __name__)

@main.route('/')
def index():

    users = User.query.all()

    # Show a welcome message to the user
    return render_template('index.html', users=users)

@main.route('/create_profile', methods=['GET','POST'])
def create_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        gender = request.form.get('gender')
        age_input = request.form.get('age')

        # Safety Check: Is age_input a number?
        if not age_input or not age_input.isdigit():
            flash("Please enter a valid age.", "error")
            return redirect(url_for('create_profile'))

        age = int(age_input)

        # The 18+ Check
        if age < 18:
            flash("You must be 18 or older to use this app.", "error")
            return redirect(url_for('create_profile'))

        new_user = UserService.create_user(username, first_name, last_name, gender, age)

        # Success message using flash function
        flash(f"The user '{username}' was successfully added")

        if new_user:
            return redirect(url_for('main.index'))
        else:
            return "Error creating user", 400

    return render_template('create_profile.html')


@main.route('/login', methods=['POST'])
def login():
    # Capture the selected ID
    user_id = request.form.get('user_id')

    # Save to Session
    session['user_id'] = user_id

    # Redirect to profile page
    return redirect(url_for('main.profile'))

@main.route('/profile')
def profile():
    # Security check
    if 'user_id' not in session:
        return redirect(url_for('main.index'))

    # Get user info
    user_id = session['user_id']
    user = UserService.get_user_by_id(user_id)

    # Get user history
    entries = JournalEntryService.get_entries_by_user(user_id)

    return render_template('profile.html', user=user, entries=entries)


@main.route('/journal', methods=['GET', 'POST'])
def journal():

    # Security check
    if 'user_id' not in session:
        return redirect(url_for('main.index'))

    if request.method == 'POST':

        # Get user info
        user_id = session['user_id']
        content = request.form.get('content')
        mood_ids = request.form.getlist('moods')

        # Create the new entry
        new_entry_obj = JournalEntryService.create_entry(user_id, content, mood_ids)

        # Get the Mood Labels (Needed for Memory)
        # We query the labels since the Vector Engine needs words ("Happy"), not IDs ("1")
        current_moods = Mood.query.filter(Mood.id.in_(mood_ids)).all()
        mood_labels = [m.label for m in current_moods]

        # Vectorize the new entry
        try:

            vector_engine.add_entry(
                entry_id=new_entry_obj.id,
                text=content,
                user_id=user_id,
                mood_tags=mood_labels
                )

        except Exception as e:
            # If the Memory Bank fails, we still want the user to proceed
            print(f"Vector Engine Error: {e}")

        # Give feedback and leave the page
        flash("Entry saved successfully! 📝")
        return redirect(url_for('main.profile'))

    # Fetch Moods for the buttons
    moods = Mood.query.all()

    # Show the Journaling Page
    return render_template('journal.html', moods=moods)

@main.route('/entry/<int:entry_id>')
def entry_detail(entry_id):

    # Security check
    if 'user_id' not in session:
        return redirect(url_for('main.index'))

    # Get the entry object
    entry = JournalEntryService.get_entry_by_id(entry_id)

    if not entry or entry.user_id != int(session['user_id']):
        return redirect(url_for('main.profile'))

    return render_template('entry_detail.html', entry=entry)

@main.route('/entry/<int:entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):

    # Security check
    if 'user_id' not in session:
        return redirect(url_for('main.index'))

    # Get the entry object
    entry = JournalEntryService.get_entry_by_id(entry_id)

    if not entry or entry.user_id != int(session['user_id']):
        return redirect(url_for('main.profile'))

    # Delete from SQL Database (The Journal)
    JournalEntryService.delete_entry_by_id(entry_id)

    # Delete from Vector Database (The Memory)
    try:
        vector_engine.delete_entry(entry_id)
    except Exception as e:
        print(f"Warning: Could not delete vector memory: {e}")

    # Give feedback and leave the page
    flash("Entry deleted successfully! 🗑️")

    return redirect(url_for('main.profile'))


@main.route('/entry/<int:entry_id>/update', methods=['GET', 'POST'])
def update_entry(entry_id):

    # Security check
    if 'user_id' not in session:
        return redirect(url_for('main.index'))

    # Get the entry object
    entry = JournalEntryService.get_entry_by_id(entry_id)

    # Ownership check
    if not entry or entry.user_id != int(session['user_id']):
        return redirect(url_for('main.profile'))

    if request.method == 'POST':

        new_content = request.form.get('new_content')
        new_mood_ids = request.form.getlist('moods')  # Capture the Mood checkboxes

        if not new_content:
            flash("Entry content can't be empty.", 'error')
            return redirect(url_for('main.entry_detail', entry_id=entry_id))

        # Update the Main Database (SQL)
        updated_entry = JournalEntryService.update_entry_by_id(entry_id, new_content, new_mood_ids)

        if updated_entry:
            # ======= SYNC START =======
            # Update the Vector DB
            try:
                # A - Delete the old memory
                vector_engine.delete_entry(entry_id)

                # B. Get the NEW mood labels
                # Since we just updated the DB, 'updated_entry.moods' has the new list.
                current_mood_tags = [m.label for m in updated_entry.moods]

                # C. Create the new memory
                vector_engine.add_entry(
                    entry_id,
                    new_content,
                    session['user_id'],
                    current_mood_tags  # Passing the list of strings of the updated entry ["Happy", "Calm"]
                )

                print(f"✅ Synced update for Entry {entry_id} in Vector DB.")

            except Exception as e:
                # If the AI update fails, don't crash the web app. Just log it.
                print(f"⚠️ Warning: Vector update failed: {e}")

            # ======= SYNC END =======

            flash("Entry updated successfully!", 'success')
            return redirect(url_for('main.entry_detail', entry_id=entry_id))
        else:
            flash("Error updating entry.", 'error')
            return redirect(url_for('main.entry_detail', entry_id=entry_id))

    # --- GET REQUEST ---
    # We need to fetch ALL moods so the user can choose from them
    all_moods = Mood.query.all()

    return render_template('edit_entry.html', entry=entry, moods=all_moods)

@main.route('/entry/<int:entry_id>/analyze', methods = ['POST'])
def analyze_entry(entry_id):
    # Security check
    if 'user_id' not in session:
        return redirect(url_for('main.index'))

    # Get the entry object
    entry = JournalEntryService.get_entry_by_id(entry_id)

    if not entry or entry.user_id != int(session['user_id']):
        return redirect(url_for('main.profile'))

    # Prepare Data for AI
    # We need to convert the mood objects (e.g., [Mood<Happy>]) into text (e.g., ["Happy"])
    mood_labels = [m.label for m in entry.moods]

    # PHASE 1: The Entry Summary Agent
    summary = SummaryAgent.analyze_sentiment(entry.content, mood_labels)

    # Save to database
    if summary:
        # SAVE POINT 1: Secure the summary immediately!
        entry.ai_summary = summary
        db.session.commit()
        #flash("AI Analysis complete! 🧠", 'success')
    else:
        flash("The summary agent could not analyze this entry. Try again later.", 'error')
        return redirect(url_for('main.entry_detail', entry_id=entry_id))

    # PHASE 2: The music recommendation agent

    try:
        # Get the user object
        user = UserService.get_user_by_id(int(session['user_id']))

        # Getting the blacklist
        # Check what the user has already heard

        excluded_songs = PastRecommendationService.get_recent_recommendations(
            user_id=int(session['user_id']),
            item_type="song"
        )

        # Call AI
        # Now returns a Python LIST of dictionaries: [{'title': 'X', 'artist': 'Y'}]
        recommendations_list = MusicRecommendationAgent.music_recommendation(
            content=entry.content,
            mood_labels=mood_labels,
            ai_summary=summary,
            age=user.age,
            gender=user.gender,
            user_name=user.username,
            excluded_songs=excluded_songs
        )

        if recommendations_list:
            # Save to history
            # This logs the specific items so we don't repeat them later
            PastRecommendationService.save_recommendations(
                user_id=int(session['user_id']),
                items=recommendations_list,
                item_type="song",
                journal_id=entry.id,
            )

            # Save to Journal Entry
            # Frontend expects a String.
            # Example result: "1. Song by Artist \n 2. Song by Artist"
            formatted_string = ""
            for i, item in enumerate(recommendations_list, 1):
                formatted_string += f"{i}. {item.get('title')} - {item.get('artist')}\n"

            entry.music_query = formatted_string
            db.session.commit()

            flash("AI Analysis & Music Curation complete! 🧠🎧", 'success')

        else:

            # It saved, but it's an error message -> YELLOW Warning
            flash("Analysis complete, but the we couldn't find songs. 🧠", 'warning')

    except Exception as e:
        print(f"Music Recommendation error: {e}")
        flash("Analysis complete, but music generation failed. 🧠", 'warning')

    return redirect(url_for('main.entry_detail', entry_id=entry_id))

@main.route('/chat', methods=['POST'])
def chat():
    # Security Check
    # If the user is not logged in, kick them out (or return error)
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Get Data (JSON style)
    # We use get_json() because the frontend sends data via JavaScript
    data = request.get_json()
    user_message = data.get('message')

    # Get the real User ID from the session
    user_id = session['user_id']

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Call the Brain!
    # Pass the REAL user_id
    ai_response = chatbox_agent.chat(user_message, str(user_id))

    # Return the answer
    return jsonify({"response": ai_response})
