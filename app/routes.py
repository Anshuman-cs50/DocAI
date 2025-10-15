from flask import Blueprint, render_template, request

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')


# Additional routes can be added here
# For example:
@main.route('/about', methods=['GET'])
def about():
    return render_template('about.html')


@main.route('/consult', methods=['GET'])
def consult():
    data = request.get_json()
    prompt = data.get('prompt', '')

    # retrieve user health matrix from database

    # generate AI response based on prompt and health matrix