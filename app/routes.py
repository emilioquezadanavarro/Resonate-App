from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from .database import db, User, Mood
from app.services.user_service import UserService
from app.services.journal_services import JournalEntryService
from app.services.ai_psychologist import AIPsychologist
from app.services.ai_recommendation import AIRecommendation

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
        age = request.form.get('age')

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
        JournalEntryService.create_entry(user_id, content, mood_ids)

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

    # Delete the entry
    JournalEntryService.delete_entry_by_id(entry_id)

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

    if not entry or entry.user_id != int(session['user_id']):
        return redirect(url_for('main.profile'))

    if request.method == 'POST':

        new_content = request.form.get('new_content')

        if not new_content:
            flash("Entry content can't be empty.", 'error')
            return redirect(url_for('main.entry_detail', entry_id=entry_id))

        updated_entry = JournalEntryService.update_entry_by_id(entry_id, new_content)

        if updated_entry:
            flash("Entry updated successfully!", 'success')
            return redirect(url_for('main.entry_detail', entry_id=entry_id))
        else:
            flash("Error updating entry.", 'error')
            return redirect(url_for('main.entry_detail', entry_id=entry_id))

    return render_template('edit_entry.html', entry=entry)

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

    # PHASE 1: The Psychologist
    summary = AIPsychologist.analyze_sentiment(entry.content, mood_labels)

    # Save to database
    if summary:
        # SAVE POINT 1: Secure the summary immediately!
        entry.ai_summary = summary
        db.session.commit()
        #flash("AI Analysis complete! 🧠", 'success')
    else:
        flash("AI could not analyze this entry. Try again later.", 'error')
        return redirect(url_for('main.entry_detail', entry_id=entry_id))

    # PHASE 2: Music Recommendation
    # We wrap this in a try/except block so a DJ failure doesn't crash the app
    try:
        music_recommendation = AIRecommendation.music_recommendation(entry.content, mood_labels, summary)

        if music_recommendation:
            # SAVE POINT 2: Secure the music recommendation!
            entry.music_query = music_recommendation
            db.session.commit()

            # CHECK: Is it the "Success" list or the "Error" message?
            if "No music found" in music_recommendation:
                # It saved, but it's an error message -> YELLOW Warning
                flash("Analysis complete, but the we couldn't find songs. 🧠", 'warning')
            else:
                # It's a real song list -> GREEN Success
                flash("AI Analysis & Music Curation complete! 🧠🎧", 'success')

        else:
            flash("Analysis complete, but the we couldn't find songs. 🧠", 'warning')

    except Exception as e:
        print(f"Music Recommendation error: {e}")
        flash("Analysis complete, but music generation failed. 🧠", 'warning')

    return redirect(url_for('main.entry_detail', entry_id=entry_id))

