from flask import Flask, request
import registration_api

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

@app.route('/api/v1/register', methods=['POST'])
def api_register():
    args = []
    # Split below into separate func
    for arg in ("username", "email", "password"):  # Check for & collect args - ORDER MATTERS
        if arg not in request.args.keys():
            return error("Bad request"), 400
        else:
            args.append(request.args.get(arg))

    api.register(*args)

if __name__ == '__main__':
    app.run()
