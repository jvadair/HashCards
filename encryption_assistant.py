from pyntree import Node
from os import getenv, path


ENCRYPTION_KEY = getenv('RAPI_AUTHKEY')
DATAKEY2 = getenv('HC_DATAKEY2')
EXPORT_KEY = getenv("EXPORT_KEY")


def get_user_db(user_id, autosave=False):
    if path.exists(f'db/users/{user_id}.pyn'):
        return Node(f'db/users/{user_id}.pyn', password=ENCRYPTION_KEY, autosave=autosave)


def get_set_db(set_id, autosave=False):
    if path.exists(f'db/sets/{set_id}.pyn'):
        return Node(f'db/sets/{set_id}.pyn', password=DATAKEY2, autosave=autosave)


def get_group_db(group_id, autosave=False):
    if path.exists(f'db/groups/{group_id}.pyn'):
        return Node(f'db/groups/{group_id}.pyn', password=ENCRYPTION_KEY, autosave=autosave)


def get_org_db(org_id, autosave=False):
    if path.exists(f'db/users/{org_id}.pyn'):
        return Node(f'db/users/{org_id}.pyn', password=ENCRYPTION_KEY, autosave=autosave)
