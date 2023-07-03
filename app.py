from flask import Flask, request, render_template, session
from registrationAPI import registration_api
from pyntree import Node
from tools import is_valid_email
from datetime import datetime
from werkzeug.exceptions import HTTPException
import os

app = Flask(__name__)
app.secret_key = os.urandom(32)
r_api = registration_api.API()
config = Node('config.json')

# Update jinja global variables
app.jinja_env.globals.update(zip=zip, len=len, Node=Node)


# Specialized page functions
def error(code, message):
    return render_template("error.html", message=message, code=code), code


# Front-end routes

@app.route('/')
def index():
    return render_template('landing.html')


@app.route('/dash')
def temp_dash_design():
    return render_template('dash.html')


@app.route('/set-manager')
def temp_set_manager_design():
    return render_template('set_manager.html', set=Node('db/sets/473ad80e-e2a5-4158-a81e-9bddf4d0aa88.pyn'), subjects=config.subjects())


@app.route('/set-viewer')
def temp_set_viewer_design():
    return render_template('set_viewer.html', set=Node('db/sets/473ad80e-e2a5-4158-a81e-9bddf4d0aa88.pyn'))


@app.route('/account-manager')
def temp_account_manager_design():
    return render_template('account_manager.html', user=Node('db/users/911fa739-6ebb-467a-af1a-0d4138135413.pyn'))


@app.route('/profile')
def temp_profile_design():
    # r_api.login(session, 'jvadair', 'password')
    return render_template('profile.html', db=Node('db/users/911fa739-6ebb-467a-af1a-0d4138135413.pyn'), type='user')


@app.route('/profile-g')
def temp_profile_design_g():
    return render_template('profile.html', db=Node('db/groups/cc6e8c4f-66b0-490f-83f6-77b43f6db0db.pyn'), type='group')


@app.route('/profile-o')
def temp_profile_design_o():
    return render_template('profile.html', db=Node('db/orgs/41699602-b74d-4972-a181-4acc0d3c0584.pyn'), type='org')


@app.route('/login')
def login_page():
    return render_template('auth.html', auth_method='login')


@app.route('/register')
def register_page():
    return render_template('auth.html', auth_method='register')


# API
@app.route('/api/v1/preregister', methods=['POST'])
def preregister():
    email = request.form['email']
    if is_valid_email(email):
        preregister_list = Node('db/preregistered.pyn')
        if email in preregister_list._values:
            return error(400, "That email is already registered!")
        preregister_list.set(email, datetime.now())
        preregister_list.save()
        return render_template("thank_you.html", message="We'll let you know as soon as you can start using HashCards!")
    else:
        return error(400, f"The email you entered, '{email}', seems to be invalid.")


@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    return error(501, "Login is not available yet.")


@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    return error(501, "Account registration is not available yet.")


# Error handling
@app.errorhandler(HTTPException)
def handle_exception(e):
    return error(e.code, e.description)


if __name__ == '__main__':
    app.run()
