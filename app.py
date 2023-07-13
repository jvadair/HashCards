from flask import Flask, request, render_template, session, Response
from registrationAPI import registration_api
from pyntree import Node
from tools import is_valid_email
from datetime import datetime
from werkzeug.exceptions import HTTPException
import os
import account_manager

app = Flask(__name__)
app.secret_key = os.urandom(32)
r_api = registration_api.API()
config = Node('config.json')

# Update jinja global variables
app.jinja_env.globals.update(zip=zip, len=len, Node=Node)


# Helper functions
def get_user_db(user_id):
    return Node(f'db/users/{user_id}.pyn', password=registration_api.ENCRYPTION_KEY)


# Specialized page functions
def error(code, message):
    return render_template("error.html", message=message, code=code), code


# Front-end routes

@app.route('/')
def index():
    return render_template('landing.html')


# @app.route('/dash')
# def temp_dash_design():
#     return render_template('dash.html')
#
#
# @app.route('/set-manager')
# def temp_set_manager_design():
#     return render_template('set_manager.html', set=Node('db/sets/473ad80e-e2a5-4158-a81e-9bddf4d0aa88.pyn'), subjects=config.subjects())
#
#
# @app.route('/set-viewer')
# def temp_set_viewer_design():
#     return render_template('set_viewer.html', set=Node('db/sets/473ad80e-e2a5-4158-a81e-9bddf4d0aa88.pyn'))


@app.route('/account')
def account_settings():
    if session['id']:
        return render_template(
            'settings.html',
            db=get_user_db(session['id']),
            type='user',
            updated=False
        )
    else:
        return error(401, "You must be logged in to manage account settings")


# @app.route('/group-manager')
# def temp_group_manager_design():
#     return render_template(
#         'settings.html',
#         db=Node('db/groups/cc6e8c4f-66b0-490f-83f6-77b43f6db0db.pyn'),
#         type='group',
#         updated=True
#     )
#
#
# @app.route('/org-manager')
# def temp_org_manager_design():
#     return render_template(
#         'settings.html',
#         db=Node('db/orgs/41699602-b74d-4972-a181-4acc0d3c0584.pyn'),
#         type='org',
#         updated=False
#     )
#
#
# @app.route('/profile')
# def temp_profile_design():
#     # r_api.login(session, 'jvadair', 'password')
#     return render_template('profile.html', db=Node('db/users/911fa739-6ebb-467a-af1a-0d4138135413.pyn'), type='user')
#
#
# @app.route('/profile-g')
# def temp_profile_design_g():
#     return render_template('profile.html', db=Node('db/groups/cc6e8c4f-66b0-490f-83f6-77b43f6db0db.pyn'), type='group')
#
#
# @app.route('/profile-o')
# def temp_profile_design_o():
#     return render_template('profile.html', db=Node('db/orgs/41699602-b74d-4972-a181-4acc0d3c0584.pyn'), type='org')
#
#
# @app.route('/members')
# def temp_member_design():
#     return render_template('member-management.html', db=Node('db/groups/cc6e8c4f-66b0-490f-83f6-77b43f6db0db.pyn'), type='group')
#
#
# @app.route('/cc')
# def temp_collective_creation_wizard_design():
#     return render_template('collective-creation.html', type='group')


@app.route('/login', methods=['GET'])
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
    data = request.form
    response = r_api.login(session, data['identifier'], data['password'], redirect='/')
    if type(response) != Response and 400 <= response[1] < 500:
        return error(*reversed(response))
    else:
        user_db = get_user_db(session['id'])
        session['pfp'] = user_db.pfp()
        return response


@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    return error(401, "Sorry, registration is not yet available. However, you can pre-register via the homepage.")  # TODO: Release this later
    # noinspection PyUnreachableCode
    data = request.form
    response = r_api.register(data['username'], data['email'], data['password'])
    if type(response) != str and 400 <= response[1] < 500:
        return error(*reversed(response))
    else:
        x = render_template("awaiting_verification.html")
        return render_template("awaiting_verification.html")


@app.route('/api/v1/verify')
def verify_user():
    token = request.args.get('token')
    user_id = r_api.verify(token)
    if type(user_id) is tuple:
        return error(*reversed(user_id))
    else:
        user_db = get_user_db(user_id)
        account_manager.update(user_db, account_manager.REQUIRED_USERS)
        session['pfp'] = user_db.pfp()
        return r_api.login(session, user_db.username(), user_db.password())


@app.route('/api/v1/auth/logout')
def logout():
    if session['id']:
        return r_api.logout(session)
    else:
        return error(400, "You are not logged in.")


# Error handling
@app.errorhandler(HTTPException)
def handle_exception(e):
    return error(e.code, e.description)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3453)
