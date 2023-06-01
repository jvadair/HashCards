from flask import Flask, request, render_template
from registrationAPI import registration_api
from pyntree import Node
from tools import is_valid_email
from datetime import datetime
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
r_api = registration_api.API()


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
