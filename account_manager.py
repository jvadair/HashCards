"""
This file ensures that all user, group, and org data files have all the necessary keys.
update should be called when a new user/group/org is added
update_all should be called when a new field is added
"""

REQUIRED_USERS = {  # Required keys and their default values
    "level": 0,
    "experience": 0,
    "sets": [],
    "groups": [],
    "orgs": []
}

REQUIRED_ORGS = {
    "members": [],
    "groups": [],
    "description": "",
}

REQUIRED_GROUPS = {
    "members": [],
    "sets": [],
    "description": "",
    "public": False,
}


import os
from pyntree import Node


def update(target: Node, requirement_set: dict):
    """
    Update a Node to ensure it conforms to the requirement set
    :param target: A user/group/org
    :param requirement_set: A set of required keys and their default values
    :return:
    """
    for field in requirement_set:
        if not target.has(field):
            target.set(field, requirement_set[field])


def update_all(users=True, groups=True, orgs=True):
    """
    Update all data files - individual sets of files can be toggled (user/group/org)
    :param users:
    :param groups:
    :param orgs:
    :return:
    """
    all_users = [
        Node(f'db/users/{user_filename}', autosave=True)
        for user_filename in os.listdir("db/users")
        if not user_filename.startswith("_map")
    ]
    all_groups = [
        Node(f'db/groups/{group_filename}', autosave=True)
        for group_filename in os.listdir("db/groups")
    ]
    all_orgs = [
        Node(f'db/orgs/{org_filename}', autosave=True)
        for org_filename in os.listdir("db/orgs")
    ]

    if users:
        for user in all_users:
            update(user, REQUIRED_USERS)

    if groups:
        for group in all_groups:
            update(group, REQUIRED_GROUPS)

    if orgs:
        for org in all_orgs:
            update(org, REQUIRED_ORGS)


if __name__ == "__main__":
    update_all()
