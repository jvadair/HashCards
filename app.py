from flask import Flask, request
from registrationAPI import registration_api

app = Flask(__name__)
r_api = registration_api.API()


# Specialized page functions
def error(message):
    return message  # Do nothing for now


# Front-end routes

@app.route('/')
def index():
    return 'Hello World!'


# API


if __name__ == '__main__':
    app.run()
