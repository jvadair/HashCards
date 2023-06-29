"""
This file ensures that all user data files have all the necessary keys.
It should be called both:
1. When a new user is added
2. When a new field is added
"""

REQUIRED = {  # Required keys and their default values
    "level": 0,
    "experience": 0,
}


import os
from pyntree import Node


def update_user(user: Node):
    for field in REQUIRED:
        if not user.has(field):
            user.set(field, REQUIRED[field])


def update_all():
    users = [
        Node(f'db/users/{user_filename}', autosave=True)
        for user_filename in os.listdir("db/users")
    ]

    for user in users:
        update_user(user)


if __name__ == "__main__":
    update_all()
