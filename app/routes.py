from flask import Blueprint, render_template, request, redirect, url_for, flash
from .database import User
from app.services.user_service import UserService

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

