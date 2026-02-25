import threading
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from .database import db, User, Mood
from app.services.user_service import UserService
from app.services.journal_services import JournalEntryService
from app.services.vector_engine import vector_engine
from app.services.ai_security_agent import security_agent
from app.services.ai_chatbox_agent import chatbox_agent
from app.services.ai_entry_summary_agent import summary_agent
from app.services.ai_music_recommendation_agent import music_recommendation_agent
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

    # Fetch Moods for the buttons
    moods = Mood.query.all()

    if request.method == 'POST':

        # Get user info
        user_id = session['user_id']
        content = request.form.get('content')
        mood_ids = request.form.getlist('moods')

        if len(content) <= 500:

            # The Security check️ (Security Agent call)
            # Verify safety BEFORE saving to the database.
            safety_status = security_agent.check_safety(content)

            if safety_status == "CRISIS":
                # STOP: Do not save. Redirect to help.
                return render_template('crisis.html', content=content, safety_page=True)

            elif safety_status == "TOXIC":
                # STOP: Do not save. Redirect to warning.
                return render_template('toxic.html', safety_page=True)

            elif safety_status == "INVALID":
                # STOP: Do not save. Redirect them back to try again.
                flash("We cound not quite understand that entry. Could you try writing it again?", "warning")
                return redirect(url_for('main.profile'))

            elif safety_status == "ERROR":
                # STOP: System Failure. Fail Closed.
                flash("Security check failed. Please try again later.", "error")
                return render_template('journal.html', moods=moods, content=content, selected_moods=mood_ids)

            # Success Path
            # Create the new entry
            new_entry_obj = JournalEntryService.create_entry(user_id, content, mood_ids)

            if new_entry_obj:

                # Get the Mood Labels (Needed for Memory)
                # We query the labels since the Vector Engine needs words ("Happy"), not IDs ("1")
                current_moods = Mood.query.filter(Mood.id.in_(mood_ids)).all()
                mood_labels = [m.label for m in current_moods]

                # Vectorize the new entry in the background
                # (Runs after the response is sent to avoid worker timeout on Render)
                # Capture values before the thread starts (thread has no Flask app context)
                _entry_id = new_entry_obj.id
                _content = content
                _user_id = user_id
                _mood_labels = list(mood_labels)

                def _vectorize_entry():
                    try:
                        vector_engine.add_entry(
                            entry_id=_entry_id,
                            text=_content,
                            user_id=_user_id,
                            mood_tags=_mood_labels
                        )
                    except Exception as e:
                        print(f"Vector Engine Error: {e}")

                threading.Thread(target=_vectorize_entry, daemon=True).start()

                # Give feedback and leave the page
                flash("Entry saved successfully! 📝")
                return redirect(url_for('main.profile'))

            else:
                # DB Failed (Locked or Error) -> Bounce back safely
                print(" Database save failed.")
                flash("System busy. Please try saving again in a moment.", "error")
                return render_template('journal.html', moods=moods, content=content, selected_moods=mood_ids)
        else:
            # Failure Path (Entry is too Long)
            flash(f"Your entry is {len(content)} characters. Please, short it to under 500.")
            return render_template('journal.html', moods=moods, content=content, selected_moods=mood_ids )

    # Show the Journaling Page (Get request)
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

    # Fetch Moods  (so they are available for both GET and POST errors)
    all_moods = Mood.query.all()

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

        # SECURITY AGENT CHECK
        safety_status = security_agent.check_safety(new_content)

        if safety_status == "CRISIS":
            # STOP everything. Do not save. Show Crisis Page.
            return render_template("crisis.html", content=new_content, safety_page=True)

        if safety_status == "TOXIC":
            # STOP everything. Do not save. Show Toxic Page.
            return render_template('toxic.html', safety_page=True)

        if safety_status == "INVALID":
            # Warn user and let them try again (redirect back to Edit page)
            flash("We couldn't quite understand that. Please write a meaningful entry.", "warning")

            # Update the entry object locally (in memory only) with what they just typed
            # This ensures the text box shows their draft, not the old DB version.
            entry.content = new_content

            # Preserve the checked moods they just clicked
            entry.moods = [Mood.query.get(m_id) for m_id in new_mood_ids]

            return render_template('edit_entry.html', entry=entry, moods=all_moods)

        if safety_status == "ERROR":
            flash("Security check failed. Please try again.", "danger")
            return render_template('edit_entry.html', entry=entry, moods=all_moods)

        # IF SAFE: Proceed to Update Database
        # Update the Main Database (SQL)
        updated_entry = JournalEntryService.update_entry_by_id(entry_id, new_content, new_mood_ids)

        if updated_entry:
            # ======= VECTOR SYNC (Background) =======
            # Runs after the response is sent to avoid worker timeout on Render
            _update_user_id = session['user_id']
            _update_mood_tags = [m.label for m in updated_entry.moods]

            def _sync_vector_db():
                try:
                    vector_engine.delete_entry(entry_id)
                    vector_engine.add_entry(
                        entry_id,
                        new_content,
                        _update_user_id,
                        _update_mood_tags
                    )
                    print(f"✅ Synced update for Entry {entry_id} in Vector DB.")
                except Exception as e:
                    print(f"⚠️ Warning: Vector update failed: {e}")

            threading.Thread(target=_sync_vector_db, daemon=True).start()
            # ======= VECTOR SYNC END =======

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
    summary = summary_agent.analyze_sentiment(entry.content, mood_labels)

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
        recommendations_list = music_recommendation_agent.music_recommendation(
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
                formatted_string += f"{i}. {item.get('title')} - {item.get('artist')}\n{item.get('reason')}\n\n"

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
