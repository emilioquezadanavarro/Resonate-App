from flask import Blueprint, render_template

# Create the Blueprint object
main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')