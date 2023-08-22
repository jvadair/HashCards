"""
This file ensures that all user, group, and org data files have all the necessary keys.
update should be called when a new user/group/org is added
update_all should be called when a new field is added
"""
import datetime

REQUIRED_USERS = {  # Required keys and their default values
    "level": 0,
    "experience": 0,
    "sets": [],
    "groups": [],
    "orgs": [],
    "pfp": "_default",
    "pinned": [],
    "socials": {},
    "recent_sets": [],
    "streak": 0,
    "streak_latest_day": datetime.datetime(1,1,1).date(),
}

REQUIRED_ORGS = {
    "members": [],
    "groups": [],
    "description": "",
    "public": False,
}

REQUIRED_GROUPS = {
    "members": [],
    "sets": [],
    "description": "",
    "public": False,
}


import os
from pyntree import Node
from encryption_assistant import get_group_db, get_set_db, get_org_db, get_user_db


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
    target.save()


def update_all(users=True, groups=True, orgs=True):
    """
    Update all data files - individual sets of files can be toggled (user/group/org)
    :param users:
    :param groups:
    :param orgs:
    :return:
    """
    all_users = [
        get_user_db(user_filename.rsplit('.', 1)[0], autosave=True)
        for user_filename in os.listdir("db/users")
        if not user_filename.startswith("_map")
    ]
    all_groups = [
        get_group_db(group_filename.rsplit('.', 1)[0], autosave=True)
        for group_filename in os.listdir("db/groups")
    ]
    all_orgs = [
        get_org_db(org_filename.rsplit('.', 1)[0], autosave=True)
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
