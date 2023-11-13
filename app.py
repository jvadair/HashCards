from flask import Flask, request, render_template, session, Response, redirect, url_for, send_from_directory
from flask_socketio import SocketIO
import hashcards
from registrationAPI import registration_api, sendmail
from authlib.integrations.flask_client import OAuth
from pyntree import Node
from tools import is_valid_email, hash_file, listdir_recursive, get_data_filenames, metatags
from datetime import datetime, timedelta
from werkzeug.exceptions import HTTPException, NotFound
import os
import account_manager
from encryption_assistant import get_user_db, get_set_db, get_org_db, get_group_db, EXPORT_KEY
import time
from sys import argv
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from zipfile import ZipFile
from uuid import uuid4
from thefuzz import fuzz
from thefuzz import process as fuzz_process
from random import shuffle
from copy import copy
from werkzeug.middleware.proxy_fix import ProxyFix
import shutil
from jinja2.exceptions import TemplateNotFound
from process_photo import process_filename, process_photo
import tarfile
from cryptography.fernet import Fernet
from flask_sitemapper import Sitemapper

app = Flask(__name__)
sitemapper = Sitemapper(app)
r_api = registration_api.API()
config = Node('config.json')
connected_clients = 0
app.config['MAX_CONTENT_PATH'] = 100 * 1000000  # mb -> bytes
app.config['TEMPLATES_AUTO_RELOAD'] = True
DEBUG = True if os.getenv('DEBUG') == "1" else False
if DEBUG:
    app.secret_key = b'hashcards is the best'
else:
    app.secret_key = os.getenv('FLASK_KEY').encode('utf8')
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
if not os.path.exists('static/images/pfp'):
    os.mkdir('static/images/pfp')
if not os.path.exists('static/images/card_images'):
    os.mkdir('static/images/card_images')


# Add socket support
socketio = SocketIO(app, max_http_buffer_size=15000000)  # 15mb max


# Update jinja global variables
app.jinja_env.globals.update(
    zip=zip,
    len=len,
    Node=Node,
    DEBUG=DEBUG,
    ADMIN=config.ADMIN(),
    get_user_db=get_user_db,
    get_set_db=get_set_db,
    get_group_db=get_group_db,
    get_org_db=get_org_db,
    max=max,
    bool=bool,
    time=time,
    metatags=metatags,
)

# Tell Flask it is behind a proxy
if not DEBUG:
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
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


# Study mode functions
def find_similar_results(set_id, looking_for, card_id):
    set_db = get_set_db(set_id)
    answer = set_db.cards.get(card_id).get(looking_for)()
    search_through = {card: set_db.cards.get(card).get(looking_for)() for card in tuple(set_db.cards().keys()) if set_db.cards.get(card).get(looking_for)().lower() != answer.lower()}
    results = fuzz_process.extract(answer, search_through, limit=3)
    results = {r[2]: r[0] for r in results}
    results[card_id] = answer
    results = list(results.items())
    shuffle(results)
    results = dict(results)
    return results


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
def update_frontend():
    os.system('git pull')


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
                try:
                    os.remove('db/temp/' + file)
                except IsADirectoryError:
                    shutil.rmtree('db/temp/' + file)
    if takeout:
        for file in os.listdir('db/takeout'):
            if datetime.now() - timedelta(minutes=age) >= datetime.fromtimestamp(os.path.getmtime('db/takeout/' + file)):
                try:
                    os.remove('db/takeout/' + file)
                except IsADirectoryError:
                    shutil.rmtree('db/takeout/' + file, )


# Front-end routes

@sitemapper.include()
@app.route('/')
def index():
    if session.get('id'):
        hashcards.check_user_streak(session['id'])
        return render_template('dash.html', user=get_user_db(session['id']))
    else:
        return render_template('landing.html', num_preregistered=len(Node('db/preregistered.pyn')._values))


@app.route('/admin')
def admin_panel():
    if session.get('id') in config.ADMIN() or DEBUG:
        num_sets = len([item for item in os.listdir('db/sets') if not item.startswith('_')])
        num_users = len([item for item in os.listdir('db/users') if not item.startswith('_')])
        num_public = len(hashcards.set_map.title._values)
        return render_template('admin.html', num_sets=num_sets, num_users=num_users, num_connected=connected_clients, num_public=num_public)
    else:
        return error(404, "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.")


@app.route("/sitemap.xml")
def sitemap():
  return sitemapper.generate()


@sitemapper.include()
@app.route('/about')
def about():
    return render_template('about.html')


@sitemapper.include(url_variables={"path": listdir_recursive('templates/learn')})
@app.route('/learn/<path:path>')
def teach_features(path):
    try:
        return render_template("learn/" + path + '.html')
    except TemplateNotFound:
        return error(404, "There are no help articles with that name. Check the URL and try again.")


@sitemapper.include(priority=0.1)
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

@sitemapper.include(priority=.4)
@app.route('/sets')
def library():
    return render_template("library.html", user=get_user_db(session.get('id')))


@sitemapper.include()
@app.route('/import')
def import_page():
    return render_template("import.html")


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


@sitemapper.include()
@app.route('/search')
def search():
    query = request.args.get('q')
    if query:
        results = tuple(hashcards.search(query).keys())
        return render_template('search.html', query=query, results=results)
    else:
        return render_template('search.html', query='', explore=hashcards.explore())


@sitemapper.include(url_variables={"target_id": get_data_filenames('db/users') + get_data_filenames('db/groups') + get_data_filenames('db/orgs')})
@app.route('/<target_id>/profile/')
def profile(target_id):
    if '_' in target_id:
        pass  # Protects map files
    elif os.path.exists(f'db/users/{target_id}.pyn'):
        db = get_user_db(target_id)
        num_public = len([s for s in db.sets() if s in hashcards.set_map.title._values])
        return render_template('profile.html', db=db, type='user', num_public=num_public)
    elif os.path.exists(f'db/groups/{target_id}'):
        db = get_group_db(target_id)
        num_public = len([s for s in db.sets() if s in hashcards.set_map.title._values])
        return render_template('profile.html', db=db, type='group', num_public=num_public)
    elif os.path.exists(f'db/orgs/{target_id}'):
        return render_template('profile.html', db=get_org_db(target_id), type='org')
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


@sitemapper.include()
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('auth.html', auth_method='login')


@sitemapper.include()
@app.route('/register')
def register_page():
    return render_template('auth.html', auth_method='register', email=request.args.get('email'))


@app.route('/takeout/<takeout_id>')
def takeout(takeout_id):
    try:
        return send_from_directory('db/takeout', f'{takeout_id}.zip', download_name="hashcards_data.zip")
    except NotFound:
        return error(400, "This data takeout link has expired or was never created.")


@sitemapper.include(priority=.3)
@app.route('/new')
def new_set():
    set_id = hashcards.create_set(session['id'])
    return redirect(f'/set/{set_id}/edit')


@sitemapper.include(url_variables={"set_id": get_data_filenames('db/sets')})
@app.route('/set/<set_id>/', methods=("GET",))
def set_viewer(set_id):
    if '_' not in set_id and os.path.exists(f'db/sets/{set_id}.pyn'):
        set_db = get_set_db(set_id)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")
    if set_db.visibility() in ('public', 'unlisted') or set_db.author() == session.get('id'):
        if session.get('id'):
            hashcards.calculate_exp_gain(session['id'], set_id, action='view')
            hashcards.update_recent_sets(session['id'], set_id)
        if set_db.cards._values:
            cards = set_db.cards.get(*set_db.cards._values)
            if type(cards) is Node:  # Account for single value being returned
                cards = [cards]
            export_text = '\n'.join([card.front._val + '\t' + card.back._val for card in cards])  # The [] ensures that single values don't throw errors
        else:
            export_text = ''
        return render_template('set_viewer.html', set=set_db, export_text=export_text)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")


@app.route('/set/<set_id>/edit/', methods=("GET",))
def set_manager(set_id):
    if hashcards.is_author(set_id, session.get('id')):
        return render_template('set_manager.html', set=get_set_db(set_id), subjects=config.subjects())
    else:
        return error(401,
                     "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts.")


@app.route('/set/<set_id>/export/')
def export_set(set_id):
    if '_' not in set_id and os.path.exists(f'db/sets/{set_id}.pyn'):
        set_db = get_set_db(set_id)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")
    if set_db.visibility() == 'public' or set_db.author() == session.get('id'):
        if not os.path.exists(f"db/temp/set_{set_id}.hcset"):
            set_db = get_set_db(set_id)
            set_db.file.password = EXPORT_KEY
            images = [set_db.cards.get(card).image() + '.png' for card in set_db.cards._values if set_db.cards.get(card).image()]
            set_db.set('image_hashes', {})
            for img in images:
                img_hash = hash_file(f'static/images/card_images/{img}')
                set_db.image_hashes.set(img.replace('.png', ''), img_hash)
            set_db.save(f"db/temp/set_data.pyn")
            with tarfile.open(f'db/temp/set_{set_id}.hcset', "w:gz") as tar:
                tar.add(f"db/temp/set_data.pyn", arcname=f"set_data.pyn")
                for img in images:
                    tar.add(f'static/images/card_images/{img}', arcname=f'img/{img}')
            os.remove(f"db/temp/set_data.pyn")
        return send_from_directory('db/temp', f'set_{set_id}.hcset', download_name=f"{set_db.title() if set_db.title() else 'New set'}.hcset")
    return error(401,
                 "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")


@app.route('/set/<set_id>/', methods=("DELETE",))
def delete_set(set_id):
    if hashcards.is_author(set_id, session.get('id')):
        hashcards.delete_set(set_id)
        return 'SUCCESS'
    else:
        return error(401,
                     "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts.")


@app.route('/set/<set_id>/study/')
def study_mode(set_id):
    if os.path.exists(f'db/sets/{set_id}.pyn'):
        set_db = get_set_db(set_id)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")
    if not session.get('id'):
        return redirect(f'/login?redirect={request.path}')
    if set_db.visibility() == 'public' or set_db.author() == session.get('id'):
        # if session.get('id'):
        #     hashcards.calculate_exp_gain(session['id'], set_id, action='view')
        #     hashcards.uupdate_recent_sets(session['id'], set_id)
        user_db = get_user_db(session['id'])
        try:
            study_db = user_db.studied_sets.get(set_id)
        except AttributeError:
            user_db.studied_sets.set(set_id, {"rounds": 0, "progress": {}})
            study_db = user_db.studied_sets.get(set_id)
            user_db.save()
        current_round = study_db.rounds() + 1
        return render_template('study.html', set=set_db, round=current_round)
    else:
        return error(401,
                     "The set is either private or does not exist. If you own this set and bookmarked it, sign in and try again.")


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
        # preregister_list.set(email, datetime.now())  # Toggle the comment to enable/disable pre-registration
        # preregister_list.save()
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
    # if not DEBUG:
    #     return error(401,
    #                  "Sorry, registration is not yet available. However, you can pre-register via the homepage.")
    # noinspection PyUnreachableCode
    data = request.form
    preregister_list = Node('db/preregistered.pyn')
    # if data['email'] not in preregister_list._values:
    #     return error(401,
    #                  "Sorry, registration is not yet available. If you pre-registered, make sure to use the email you did so with.")
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
    elif type(user_id) is str:
        user_db = get_user_db(user_id)
        account_manager.update(user_db, account_manager.REQUIRED_USERS)
        account_manager.update(user_db.email_preferences, account_manager.REQUIRED_EMAIL_PREFERENCES)
        session['pfp'] = user_db.pfp()
        return r_api.login(session, user_db.username(), user_db.password())
    else:
        return redirect('/account?updated=true')


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


@app.route('/api/v1/set/import/', methods=['POST'])
def import_set():
    data = request.form
    file = request.files.get('file')
    if session.get('id'):
        if file:
            set_id = hashcards.import_set(session['id'], file, data_type='file')
        else:
            set_id = hashcards.import_set(session['id'], data['text'], data_type='text')
            hashcards.modify_set(set_id, title=data['title'])
        if set_id:
            return redirect(f'/set/{set_id}')
        else:
            return error("400", "HashCards couldn't understand the file you uploaded. Check to make sure you uploaded the right file. The file you provided is either corrupt or outdated.")
    else:
        return error(401, "You must be logged in to import a set.")

# Sockets


# Connection count
@socketio.on("connect")
def connect():
    global connected_clients
    connected_clients += 1


@socketio.on("disconnect")
def disconnect():
    global connected_clients
    connected_clients -= 1


# Set saving
@socketio.on("update_set")
def perform_update(data):
    data = list(data)
    set_id = data[0]
    actions = list(data[1].values())
    if hashcards.is_author(set_id, session.get('id')):
        for action_id, data in actions:
            if action_id == "delete_card":
                try:
                    hashcards.delete_card(set_id, data)
                except AttributeError:
                    pass
            elif action_id == "change_position":
                hashcards.move_card(set_id, data['initial'], data['final'])
            else:
                hashcards.modify_set(set_id, **{action_id: data})

        return 'success'
    # set_id = data.pop('set_id')
    # if hashcards.is_author(set_id, session.get('id')):
    #     hashcards.modify_set(set_id, **data)
    #     return 'success'
    else:
        return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


@socketio.on("update_cards")
def update_cards(data):
    set_id = data.pop('set_id')
    set_db = get_set_db(set_id)
    if hashcards.is_author(set_id, session.get('id')):
        for card_id in data:
            if card_id not in set_db.card_order() and not hashcards.add_card(set_id, card_id=card_id):  # Attempt to create if not exists
                return False
            hashcards.modify_card(set_id, card_id, **data[card_id])
    return "success"


# @socketio.on("update_card")
# def perform_card_update(data):
#     print(data)
#     set_id = data.pop('set_id')
#     card_id = data.pop('card_id')
#     if hashcards.is_author(set_id, session.get('id')):
#         hashcards.modify_card(set_id, card_id, **data)
#         return 'success'
#     else:
#         return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


# @socketio.on("new_card")
# def add_new_card(data):
#     try:
#         set_id = data.pop('set_id')
#         if hashcards.is_author(set_id, session.get('id')):
#             card_id = hashcards.add_card(set_id)
#             return hashcards.get_card(set_id, card_id)()
#         else:
#             return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."
#     except KeyError:
#         return 400, "That card doesn't exist"


# @socketio.on("delete_card")
# def delete_card(data):
#     set_id = data.pop('set_id')
#     if hashcards.is_author(set_id, session.get('id')):
#         card_id = data['card_id']
#         hashcards.delete_card(set_id, card_id)
#         return 'success'
#     else:
#         return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."
#
#
# @socketio.on("change_position")
# def change_card_position(data):
#     set_id = data.pop('set_id')
#     if hashcards.is_author(set_id, session.get('id')):
#         hashcards.move_card(set_id, data['initial'], data['final'])
#         return 'success'
#     else:
#         return 401, "You are not the author of this set, so you can't edit it. If you do happen to be the owner, please try switching accounts."


@socketio.on("add_image")
def add_image(data):
    set_id = data['set_id']
    card_id = data['card_id']
    filename = data['filename']
    if session.get('id'):
        if hashcards.is_author(set_id, session['id']):
            image_id = str(uuid4())
            filename = process_filename(filename)
            if filename:
                extension = filename.rsplit('.', maxsplit=1)[1]
                with open(f'db/temp/{image_id}.{extension}', 'wb') as file:
                    file.write(data['file'])
                new_filename = process_photo(f'db/temp/{image_id}.{extension}')
                os.rename(new_filename, f'static/images/card_images/{image_id}.png')
                set_db = get_set_db(set_id)
                if card_id not in set_db.card_order() and not hashcards.add_card(set_id, card_id=card_id):  # Attempt to create if not exists
                    return False
                hashcards.modify_card(set_id, card_id, image=image_id)
                return image_id
    return 401, "You are not signed in."


@socketio.on("remove_image")
def add_image(data):
    set_id = data['set_id']
    card_id = data['card_id']
    if session.get('id'):
        if hashcards.is_author(set_id, session['id']):
            set_db = get_set_db(set_id)
            image_id = set_db.cards.get(card_id).image()
            os.remove(f'static/images/card_images/{image_id}.png')
            hashcards.modify_card(set_id, card_id, image=None)
            return 200, 'OK'
    return 401, "You are not signed in."


# Share from the set viewer page
@socketio.on("make_public")
def make_public(data):
    set_id = data['set_id']
    if session.get('id'):
        if hashcards.is_author(set_id, session['id']):
            hashcards.modify_set(set_id, visibility='public')
            return 200
    return 401, "You must be logged in to make a a set public."


# Study mode
@socketio.on("study_next")
def generate_next_prompt(data):
    if session.get('id'):
        set_id = data.pop('set_id')
        set_db = get_set_db(set_id)
        if set_db.visibility() == 'public' or set_db.author() == session.get('id'):
            user_db = get_user_db(session['id'])
            study_db = user_db.studied_sets.get(set_id)
            card_list = copy(set_db.card_order())
            shuffle(card_list)
            found = False
            for card_id in card_list:  # Loop until card found
                try:
                    card_progress = study_db.progress.get(card_id)()
                    if card_progress < 3:
                        found = True
                        break
                except AttributeError:
                    study_db.progress.set(card_id, 0)
                    card_progress = 0
                    found = True
                    break
            if not found:
                study_db.rounds += 1
                card_id = card_list[0]
                study_db.set("progress", {card_id: 0})
                card_progress = 0
            user_db.save()
            looking_for = 'front' if card_progress < 1 else 'back'
            session['currently_studying'] = card_id
            session['current_card_side'] = looking_for
            if card_progress in (0, 2):
                options = find_similar_results(set_id, 'front' if looking_for == 'back' else 'back', card_id)
                return {"type": "mc", "side": looking_for, "question": set_db.cards.get(card_id).get(looking_for)(), "options": options, "round": study_db.rounds() + 1}
            else:
                return {"type": "sr", "side": looking_for, "question": set_db.cards.get(card_id).get(looking_for)(), "round": study_db.rounds() + 1}
    else:
        return error(401, "You must be signed in to use study mode.")


@socketio.on("check_answer")
def check_answer(data):
    if session.get('id') and session.get("currently_studying"):
        set_id = data.pop('set_id')
        set_db = get_set_db(set_id)
        card_id = data.get('card_id')
        prompt_response = data.get('answer')
        correct_card_id = session.get('currently_studying')
        del session['currently_studying']
        if card_id:
            if correct_card_id == card_id:
                user_db = get_user_db(session.get('id'))
                study_db = user_db.studied_sets.get(set_id)
                card_progress = study_db.progress.get(card_id)
                card_progress += 1
                user_db.save()
                hashcards.calculate_exp_gain(session['id'], set_id, "study_card")
                return {"success": True}
            else:
                return {"success": False, "correct": correct_card_id}
        elif prompt_response is not None:  # Could be empty string
            correct_answer = set_db.cards.get(correct_card_id).get('back' if session['current_card_side'] == 'front' else 'front')()
            accuracy = fuzz.ratio(correct_answer.lower(), prompt_response.lower())
            if accuracy >= 95:
                user_db = get_user_db(session.get('id'))
                study_db = user_db.studied_sets.get(set_id)
                card_progress = study_db.progress.get(correct_card_id)
                card_progress += 1
                user_db.save()
                hashcards.calculate_exp_gain(session['id'], set_id, "study_card")
                return {"success": True, "correct": correct_answer, "accuracy": accuracy}
            else:
                return {"success": False, "correct": correct_answer}
    elif not session.get("id"):
        return error(401, "You must be signed in to use study mode.")
    else:
        return error(400, "No card is currently being studied.")


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
        account_manager.update(user_db.email_preferences, account_manager.REQUIRED_EMAIL_PREFERENCES)
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
    preregister_list = Node('db/preregistered.pyn')
    username = email.split('@gmail.com')[0]  # This will look weird for non-gmails, but solves potential conflicts
    # if email not in preregister_list._values and username not in registration_api.socials.google._values:
    #     return error(401,
    #                  "Sorry, registration is not yet available. If you pre-registered, make sure to use the email you did so with.")
    was_created = r_api.handle_social_login(username, 'google', session)
    user_db = get_user_db(session['id'])
    if was_created:
        account_manager.update(user_db, account_manager.REQUIRED_USERS)
        account_manager.update(user_db.email_preferences, account_manager.REQUIRED_EMAIL_PREFERENCES)
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
    scheduler.add_job(func=update_frontend, trigger="interval", hours=1)
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
