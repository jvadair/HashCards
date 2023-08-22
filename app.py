from flask import Flask, request, render_template, session, Response, redirect, url_for, send_from_directory
from flask_socketio import SocketIO
import hashcards
from registrationAPI import registration_api, sendmail
from authlib.integrations.flask_client import OAuth
from pyntree import Node
from tools import is_valid_email
from datetime import datetime, timedelta
from werkzeug.exceptions import HTTPException, NotFound
import os
import account_manager
from encryption_assistant import get_user_db, get_set_db, get_org_db, get_group_db
import time
from sys import argv
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from zipfile import ZipFile
from uuid import uuid4

app = Flask(__name__)
app.secret_key = os.urandom(32)
r_api = registration_api.API()
config = Node('config.json')
DEBUG = True if os.getenv('DEBUG') == "1" else False
SCHEME = 'http' if DEBUG else 'https'
LOGIN_REQUIRED = (
    "/new",
    "/sets",
    "/oauth/google/link",
    "/oauth/nexus/link",
    "/oauth/google/unlink",
    "/oauth/nexus/unlink",
)
HIDE_WHEN_LOGGED_IN = (
    "/login",
    "/register"
)

# First-run or reset scenario
if not os.path.exists('db/sets'):
    os.mkdir('db/sets')
if not os.path.exists('db/temp'):
    os.mkdir('db/temp')
if not os.path.exists('db/takeout'):
    os.mkdir('db/takeout')


# Add socket support
socketio = SocketIO(app)


# Update jinja global variables
app.jinja_env.globals.update(
    zip=zip,
    len=len,
    Node=Node,
    DEBUG=DEBUG,
    get_user_db=get_user_db,
    get_set_db=get_set_db,
    get_group_db=get_group_db,
    get_org_db=get_org_db,
    max=max
)

# OAuth setup
oauth = OAuth(app)
oauth.register(
    name='nexus',
    client_id=os.getenv('NEXUS_CLIENT_ID'),
    client_secret=os.getenv('NEXUS_CLIENT_SECRET'),
    access_token_url='https://nexus.jvadair.com/index.php/apps/oauth2/api/v1/token',
    access_token_params=None,
    authorize_url='https://nexus.jvadair.com/index.php/apps/oauth2/authorize',
    authorize_params=None,
    # api_base_url='https://graph.facebook.com/',
    client_kwargs=None,
)
oauth.register(
    name='nexus_link',
    client_id=os.getenv('NEXUS_LINK_CLIENT_ID'),
    client_secret=os.getenv('NEXUS_LINK_CLIENT_SECRET'),
    access_token_url='https://nexus.jvadair.com/index.php/apps/oauth2/api/v1/token',
    access_token_params=None,
    authorize_url='https://nexus.jvadair.com/index.php/apps/oauth2/authorize',
    authorize_params=None,
    # api_base_url='https://graph.facebook.com/',
    client_kwargs=None,
)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        'scope': 'openid email'
    }
)


# Specialized page functions
def error(code, message):
    return render_template("error.html", message=message, code=code), code


# Additional helper functions
def zip_user_data(user_id, create_link=True, send_email=True):
    user_db = get_user_db(user_id)
    user_db.file.password = None
    user_db.delete('password')
    user_db.crtime = time.mktime(user_db.crtime().timetuple())
    user_db.streak_latest_day = time.mktime(user_db.streak_latest_day().timetuple())
    user_db.save(f"db/temp/_account_{user_id}.json")
    filenames = [f"db/temp/_account_{user_id}.json"]
    for set in user_db.sets():
        set_db = get_set_db(set)
        set_db.file.password = None
        set_db.crtime = time.mktime(set_db.crtime().timetuple())
        set_db.mdtime = time.mktime(set_db.mdtime().timetuple())
        set_db.save(f"db/temp/set_{set}.json")
        filenames.append(f"db/temp/set_{set}.json")
    with ZipFile(f"db/temp/dataexport_{user_id}.zip", mode="w") as archive:
        for filename in filenames:
            archive.write(filename, filename.replace('db/temp/', ''))
            os.remove(filename)
    if create_link:
        takeout_id = str(uuid4())
        os.rename(f"db/temp/dataexport_{user_id}.zip", f"db/takeout/{takeout_id}.zip")
        if send_email:
            sendmail.send_template('email/datarequest.html',
                                   "Here's your HashCards data!",
                                   user_db.email(),
                                   date_and_time=datetime.now().strftime("%A %B %-m at %X"),
                                   takeout_id=takeout_id,
                                   )
        return takeout_id


# Update all account data with required keys, if requested
if 'accupdate' in argv:
    account_manager.update_all()


# Background workers
def clear_files(age=0, temporary=True, takeout=True):
    """
    :param takeout: Delete takeout data
    :param temporary: Delete temporary data
    :param age: How long the data has existed, in minutes
    :return:
    """
    if temporary:
        for file in os.listdir('db/temp'):
            if datetime.now() - timedelta(minutes=age) >= datetime.fromtimestamp(os.path.getmtime('db/temp/' + file)):
                os.remove('db/temp/' + file)
    if takeout:
        for file in os.listdir('db/takeout'):
            if datetime.now() - timedelta(minutes=age) >= datetime.fromtimestamp(os.path.getmtime('db/takeout/' + file)):
                os.remove('db/takeout/' + file)


# Front-end routes


@app.route('/')
def index():
    if session.get('id'):
        hashcards.check_user_streak(session['id'])
        return render_template('dash.html', user=get_user_db(session['id']))
    else:
        return render_template('landing.html', num_preregistered=len(Node('db/preregistered.pyn')._values))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/account')
def account_settings():
    if session.get('id'):
        return render_template(
            'settings.html',
            db=get_user_db(session['id']),
            type='user',
            updated=request.args.get('updated')
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

@app.route('/sets')
def library():
    return render_template("library.html", user=get_user_db(session.get('id')), time=time)


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
@app.route('/<target_id>/profile/')
def profile(target_id):
    if os.path.exists(f'db/users/{target_id}.pyn'):
        return render_template('profile.html', db=get_user_db(target_id), type='user')
    elif os.path.exists(f'db/groups/{target_id}'):
        return render_template('profile.html', db=get_group_db(target_id), type='group')
    if os.path.exists(f'db/orgs/{target_id}'):
        return render_template('profile.html', db=get_org_db(target_id), type='org')
    else:
        return error(404, "There are no users, groups, or organizations with that ID.")
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


@app.route('/takeout/<takeout_id>')
def takeout(takeout_id):
    try:
        return send_from_directory('db/takeout', f'{takeout_id}.zip', download_name="hashcards_data.zip")
    except NotFound:
        return error(400, "This data takeout link has expired or was never created.")


@app.route('/new')
def new_set():
    set_id = hashcards.create_set(session['id'])
    return redirect(f'/set/{set_id}/edit')


@app.route('/set/<set_id>/', methods=("GET",))
def set_viewer(set_id):
    if os.path.exists(f'db/sets/{set_id}.pyn'):
        set_db = get_set_db(set_id)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")
    if set_db.visibility() == 'public' or set_db.author() == session.get('id'):
        if session.get('id'):
            hashcards.calculate_exp_gain(session['id'], set_id, action='view')
            hashcards.update_recent_sets(session['id'], set_id)
        return render_template('set_viewer.html', set=set_db)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")


@app.route('/set/<set_id>/edit/', methods=("GET",))
def set_manager(set_id):
    if hashcards.is_author(set_id, session.get('id')):
        return render_template('set_manager.html', set=get_set_db(set_id))
    else:
        return error(401,
                     "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts.")


@app.route('/set/<set_id>/', methods=("DELETE",))
def delete_set(set_id):
    if hashcards.is_author(set_id, session.get('id')):
        hashcards.delete_set(set_id)
        return 'SUCCESS'
    else:
        return error(401,
                     "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts.")


# API

# Authentication/registration
@app.route('/api/v1/preregister', methods=['POST'])
def preregister():
    email = request.form['email']
    if session.get('pre-registered'):
        return error(401, "You may only pre-register one email (to prevent spam).")
    elif is_valid_email(email):
        preregister_list = Node('db/preregistered.pyn')
        if email in preregister_list._values:
            return error(400, "That email is already registered!")
        preregister_list.set(email, datetime.now())
        preregister_list.save()
        session['pre-registered'] = True
        sendmail.send_template('email/preregister.html', "You pre-registered for HashCards!", email)
        return render_template("thank_you.html", message="We'll let you know as soon as you can start using HashCards!")
    else:
        return error(400, f"The email you entered, '{email}', seems to be invalid.")


@app.route('/api/v1/unsubscribe/')
def unsubscribe():
    unsub_id = request.args.get('unsub_id')
    response = sendmail.unsubscribe(unsub_id)
    if response is tuple:
        return error(*reversed(tuple))
    else:
        return response


@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.form
    response = r_api.login(session, data['identifier'], data['password'], redirect=data['redirect'])
    if type(response) is tuple and 400 <= response[1] < 500:
        return error(*reversed(response))
    else:
        user_db = get_user_db(session['id'])
        session['pfp'] = user_db.pfp()
        return response


@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    if not DEBUG:
        return error(401,
                     "Sorry, registration is not yet available. However, you can pre-register via the homepage.")  # TODO: Release this later
    # noinspection PyUnreachableCode
    data = request.form
    response = r_api.register(data['username'], data['email'], data['password'])
    if type(response) != str and 400 <= response[1] < 500:
        return error(*reversed(response))
    else:
        return render_template("awaiting_verification.html")


@app.route('/api/v1/verify')
def verify_user():
    token = request.args.get('token')
    user_id = r_api.verify(token)  # Returns user ID or error
    if type(user_id) is Response:
        return user_id  # r_api.verify returns a redirect if verifying an email change
    elif type(user_id) is tuple:
        return error(*reversed(user_id))
    else:
        user_db = get_user_db(user_id)
        account_manager.update(user_db, account_manager.REQUIRED_USERS)
        session['pfp'] = user_db.pfp()
        return r_api.login(session, user_db.username(), user_db.password())


@app.route('/api/v1/auth/logout')
def logout():
    if session.get('id'):
        return r_api.logout(session)
    else:
        return error(400, "You are not logged in.")


# User management
@app.route('/api/v1/account', methods=('DELETE',))
def delete_account():
    user_id = session.get('id')
    if user_id:
        r_api.logout(session)
        r_api.delete_account(user_id)
        return 'OK'
    else:
        return error(401, "You cannot delete an account you aren't signed in with.")


@app.route('/api/v1/account/email', methods=('POST',))
def change_email():
    if session.get('id'):
        data = request.form
        new_email = data.get('email')
        if new_email:
            if is_valid_email(new_email):
                response = r_api.change_email(session['id'], new_email)
                if type(response) is tuple:
                    return error(*reversed(response))
                return render_template("awaiting_verification.html")
            return error(400, "Please provide a valid email!")
        else:
            return error(400, "A new email address was not provided.")
    else:
        return error(401, "You cannot change the email of an account you aren't signed in with.")


@app.route('/api/v1/account/username', methods=('POST',))
def change_username():
    if session.get('id'):
        data = request.form
        new_username = data.get('username')
        if new_username:
            response = r_api.change_username(session['id'], new_username)
            if type(response) is tuple:
                return error(*reversed(response))
            return redirect("/account?updated=True")
        else:
            return error(400, "A new username was not provided.")
    else:
        return error(401, "You cannot change the username of an account you aren't signed in with.")


@app.route('/api/v1/account/password', methods=('POST',))
def change_password():
    if session.get('id'):
        data = request.form
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        user_db = get_user_db(session['id'])
        if old_password != user_db.password():
            return error(401, "Incorrect password, please try again.")
        if new_password:
            response = r_api.change_password(session['id'], new_password)
            if type(response) is tuple:
                return error(*reversed(response))
            return redirect("/account?updated=True")
        else:
            return error(400, "A new password was not provided.")
    else:
        return error(401, "You cannot change the password for an account you aren't signed in with.")


@app.route('/api/v1/account/request_data', methods=('POST',))
def request_data():
    if session.get('id'):
        scheduler.add_job(zip_user_data, args=(session['id'],))
        return render_template('success.html', message='You should see an email shortly. You will have approximately 1 week to download the data before it is deleted from our servers.')
    else:
        return error(401, "You cannot change the username of an account you aren't signed in with.")


@app.route('/api/v1/account/email_preferences', methods=('POST',))
def change_email_preferences():
    if session.get('id'):
        data = dict(request.form)
        user_db = get_user_db(session['id'])
        for option in ('updates', 'requests'):
            if data.get(option):
                user_db.email_preferences.set(option, True)
            else:
                user_db.email_preferences.set(option, False)
        user_db.save()
        return redirect("/account?updated=True")
    else:
        return error(401, "You cannot change email preferences for an account you aren't signed in with.")


@app.route('/api/v1/account/pin/', methods=['POST'])
def pin_set():
    data = request.json
    if session.get('id'):
        user_db = get_user_db(session['id'])
        set_id = data['set_id']
        if set_id in user_db.pinned():
            user_db.pinned().remove(set_id)
        else:
            user_db.pinned().append(data['set_id'])
        user_db.save()
        return 'OK'
    else:
        return error(401, "You must be logged in to pin a set.")

# Sockets

@socketio.on("update_set")
def perform_update(data):
    set_id = data.pop('set_id')
    if hashcards.is_author(set_id, session.get('id')):
        hashcards.modify_set(set_id, **data)
        return 'success'
    else:
        return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


@socketio.on("update_card")
def perform_card_update(data):
    set_id = data.pop('set_id')
    card_id = data.pop('card_id')
    if hashcards.is_author(set_id, session.get('id')):
        hashcards.modify_card(set_id, card_id, **data)
        return 'success'
    else:
        return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


@socketio.on("new_card")
def add_new_card(data):
    try:
        set_id = data.pop('set_id')
        if hashcards.is_author(set_id, session.get('id')):
            card_id = hashcards.add_card(set_id)
            return hashcards.get_card(set_id, card_id)()
        else:
            return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."
    except KeyError:
        return 400, "That card doesn't exist"


@socketio.on("delete_card")
def delete_card(data):
    set_id = data.pop('set_id')
    if hashcards.is_author(set_id, session.get('id')):
        card_id = data['card_id']
        hashcards.delete_card(set_id, card_id)
        return 'success'
    else:
        return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


@socketio.on("change_position")
def change_card_position(data):
    set_id = data.pop('set_id')
    if hashcards.is_author(set_id, session.get('id')):
        hashcards.move_card(set_id, data['initial'], data['final'])
        return 'success'
    else:
        return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


# OAuth routes
@app.route('/oauth/nexus/')
def nexus():
    link = request.args.get('link')  # Will either be None or 'true'
    session['oauth_redirect'] = request.args.get('redirect')
    if link and session.get('id'):
        redirect_uri = url_for('nexus_link', _external=True, _scheme=SCHEME)
        return oauth.nexus_link.authorize_redirect(redirect_uri)
    else:
        redirect_uri = url_for('nexus_auth', _external=True, _scheme=SCHEME)
        return oauth.nexus.authorize_redirect(redirect_uri)


@app.route('/oauth/google/')
def google():
    link = request.args.get('link')  # Will either be None or 'true'
    session['oauth_redirect'] = request.args.get('redirect')
    if link and session.get('id'):
        redirect_uri = url_for('google_link', _external=True, _scheme=SCHEME)
    else:
        redirect_uri = url_for('google_auth', _external=True, _scheme=SCHEME)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/oauth/nexus/auth/')
def nexus_auth():
    token = oauth.nexus.authorize_access_token()
    # resp = oauth.nexus.get('...')
    # user = oauth.nexus.parse_id_token(token)
    # userinfo = token['userinfo']
    # profile = resp.json()
    # log.debug("Nexus login:", token['user_id'])
    # log.debug("Token:", token)
    was_created = r_api.handle_social_login(token['user_id'], 'nexus', session)
    user_db = get_user_db(session['id'])
    if was_created:
        account_manager.update(user_db, account_manager.REQUIRED_USERS)
    session['pfp'] = user_db.pfp()
    redirect_location = session.get("oauth_redirect")
    return redirect(redirect_location if redirect_location else '/')


@app.route('/oauth/google/auth/')
def google_auth():
    token = oauth.google.authorize_access_token()
    # resp = oauth.nexus.get('...')
    # user = oauth.nexus.parse_id_token(token)
    # userinfo = token['userinfo']
    # profile = resp.json()
    # print("Google login:", token['user_id'])
    # print("Google token:", token)
    email = token['userinfo']['email']
    username = email.split('@gmail.com')[0]  # This will look weird for non-gmails, but solves potential conflicts
    was_created = r_api.handle_social_login(username, 'google', session)
    user_db = get_user_db(session['id'])
    if was_created:
        account_manager.update(user_db, account_manager.REQUIRED_USERS)
    session['pfp'] = user_db.pfp()
    redirect_location = session.get("oauth_redirect")
    del session['oauth_redirect']
    return redirect(redirect_location if redirect_location else '/')


@app.route('/oauth/nexus/link')
def nexus_link():
    token = oauth.nexus_link.authorize_access_token()
    success = r_api.link_social_account(session['id'], token['user_id'], 'nexus')
    if success:
        return redirect('/account?updated=True')
    else:
        return error(400, "Before you can link this account, it must be unlinked from the HashCards account it is currently linked to.")


@app.route('/oauth/google/link')
def google_link():
    token = oauth.google.authorize_access_token()
    email = token['userinfo']['email']
    username = email.split('@gmail.com')[0]
    success = r_api.link_social_account(session['id'], username, 'google')
    if success:
        return redirect('/account?updated=True')
    else:
        return error(400, "Before you can link this account, it must be unlinked from the HashCards account it is currently linked to.")


@app.route('/oauth/<platform>/unlink/')
def unlink_account(platform):
    if platform in ('google', 'nexus'):
        user_db = get_user_db(session['id'])
        success = r_api.unlink_social_account(session['id'], platform)
        if success:
            return redirect('/account?updated=True')
        else:
            return error(400, f"You have not linked a {platform} account.")
    else:
        return 404


# Legal stuff
@app.route('/terms')
def tos():
    return render_template('terms.html')


@app.route('/privacy-policy')
def privacypolicy():
    return render_template('privacy-policy.html')


# Login-restricted pages
@app.before_request
def check_permissions():
    if request.path in LOGIN_REQUIRED and not session.get('id'):
        return error(401, "You must be logged in to view this page.")
    elif request.path in HIDE_WHEN_LOGGED_IN and session.get('id'):
        return error(400, "You are already logged in!")


# Error handling
@app.errorhandler(HTTPException)
def handle_exception(e):
    return error(e.code, e.description)


if __name__ == '__main__':
    # Configure background tasks
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: registration_api.clear_unverified_accounts(age=24*60), trigger="interval", hours=1)
    scheduler.add_job(func=lambda: clear_files(age=7 * 24 * 60), trigger="interval", seconds=1)
    scheduler.start()
    # Run
    if DEBUG:
        socketio.run(
            app,
            host="0.0.0.0",
            port=3453,
            allow_unsafe_werkzeug=True,
            debug=True,
            use_reloader=False  # Ensure app isn't run twice when loaded
        )
    else:
        socketio.run(
            app,
            host="0.0.0.0",
            port=3453,
        )

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
