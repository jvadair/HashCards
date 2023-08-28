"""
hashcards.py
============
This file contains the essential backend functions needed to create and modify sets.
It does not contain other essential high-level functions such as account management.
"""

from pyntree import Node
from encryption_assistant import get_group_db, get_set_db, get_org_db, get_user_db, DATAKEY2
from datetime import datetime, timedelta
from copy import copy
from uuid import uuid4
import os

SET_TEMPLATE = {
    "id": None,
    "title": "Unnamed set",
    "description": "",
    "author": None,
    "crtime": None,
    "mdtime": None,
    "group": None,
    "visibility": 'private',
    "cards": {},
    "card_order": [],
    "subject": "",
    "views": [],
    "autosave": True,
}
SET_NOMODIFY = (
    "id",
    "author",
    "crtime",
    "mdtime",
    "cards",
    "card_order",  # This is only to be modified by the move_card function
    "views",
)

CARD_TEMPLATE = {
    "id": None,
    "front": None,
    "back": None,
    "image": None,
}
CARD_NOMODIFY = (
    "id"
)


def create_set(
        user_id: str,
        title: str = "",
        subject: str = None,
        org_id: str = None,
        group_id: str = None,
        is_public: bool = False) -> str:
    """
    Create a new set and save it
    :param user_id:
    :param title:
    :param subject:
    :param org_id:
    :param group_id:
    :param is_public:
    :return: The set id
    """
    template = copy(SET_TEMPLATE)
    set = Node(template)
    author = get_user_db(user_id)
    set.id = str(uuid4())
    set.title = title
    set.author = user_id
    set.crtime = datetime.now()
    set.mdtime = datetime.now()
    set.group = group_id
    set.public = is_public
    set.subject = subject
    set.save(f"db/sets/{set.id()}.pyn", password=DATAKEY2)
    author.sets().append(set.id())
    author.save()
    return set.id()


def modify_set(set_id, **kwargs) -> None:
    """
    Modify an existing set and save it
    """
    set = get_set_db(set_id)
    for kwarg in kwargs:
        if kwarg in SET_TEMPLATE and kwarg not in SET_NOMODIFY:
            if kwarg == 'visibility' and kwargs[kwarg] not in ('private', 'public', 'group'):
                continue
            if kwarg in ('autosave',):  # Bool type-forcer
                set.set(kwarg, bool(kwargs[kwarg]))
            elif type(kwargs[kwarg]) not in (str, int) or len(kwargs[kwarg]) > 100000:  # Prevent spammers and whatnot
                continue
            set.set(kwarg, kwargs[kwarg])
    set.mdtime = datetime.now()
    set.save()


def delete_set(set_id: str) -> None:
    """
    Delete the specified set
    :param set_id:
    :return:
    """
    set = get_set_db(set_id)
    author = get_user_db(set.author())
    author.sets().remove(set_id)
    author.save()
    if set.group():
        group = get_group_db(set.group())
        group.sets().remove(set_id)
        group.save()
    os.remove(f"db/sets/{set_id}.pyn")


def create_card(front: str, back: str, image: str) -> dict:
    """
    Create a new card from the template and return it
    :param front:
    :param back:
    :param image:
    :return:
    """
    card = copy(CARD_TEMPLATE)
    card['id'] = str(uuid4())
    card['front'] = front
    card['back'] = back
    card['image'] = image
    return card


def add_card(set_id: str, front: str = '', back: str = '', image: str = None):
    """
    Add a new card to the specified set
    :param set_id:
    :param front:
    :param back:
    :param image:
    :return:
    """
    card = create_card(front, back, image=image)
    set = get_set_db(set_id)
    set.cards.set(card['id'], card)
    set.card_order().append(card['id'])
    set.mdtime = datetime.now()
    set.save()
    return card['id']


def get_card(set_id, card_id):
    """
    Get a card from a set ID and card ID
    :param set_id:
    :param card_id:
    :return: Card as Node
    """
    return get_set_db(set_id).cards.get(card_id)


def modify_card(set_id, card_id, **kwargs) -> None:
    """
    Modify a card in a specified set
    :param set_id:
    :param card_id:
    :param kwargs:
    :return:
    """
    set = get_set_db(set_id)
    card = set.cards.get(card_id)
    for kwarg in kwargs:
        if kwarg in CARD_TEMPLATE and kwarg not in CARD_NOMODIFY:
            if type(kwargs[kwarg]) not in (str, int) or len(kwargs[kwarg]) > 100000:
                continue
            card.set(kwarg, kwargs[kwarg])
    set.mdtime = datetime.now()
    set.save()


def delete_card(set_id, card_id) -> None:
    """
    Delete a card from a specified set
    :param set_id:
    :param card_id:
    :return:
    """
    set = get_set_db(set_id)
    set.cards.delete(card_id)
    set.card_order().remove(card_id)
    set.mdtime = datetime.now()
    set.save()


def move_card(set_id, initial, final):
    set = get_set_db(set_id)
    card_id = set.card_order().pop(initial)
    set.card_order().insert(final, card_id)
    set.save()


def import_set(user_id, text):
    # Splitting by \t first allows us to use rsplit with a max of 1 to preserve intentional newlines
    text_split = text.split('\t')
    text_split = [x.rsplit('\n', maxsplit=1) for x in text_split]
    cards = []
    for i in range(0,len(text_split)-1):
        cards.append((text_split[i][-1], text_split[i+1][0]))  # The -1 ensures that the first item works too
    set_id = create_set(user_id)
    for card in cards:
        try:
            add_card(set_id, card[0], card[1])
        except KeyError:
            pass
    return set_id


def is_author(set_id: str, author_id: str) -> bool:
    """
    Determine whether the specified user is the author of the specified set
    :param set_id:
    :param author_id:
    :return: True or False
    """
    if not os.path.exists(f'db/sets/{set_id}.pyn'):
        return False
    set = get_set_db(set_id)
    if set.author() == author_id:
        return True
    else:
        return False


def update_recent_sets(user_id, set_id):
    user_db = get_user_db(user_id)
    try:  # Don-t re-add sets, just change their place
        user_db.recent_sets().remove(set_id)
    except ValueError:
        pass
    user_db.recent_sets().insert(0, set_id)
    user_db.save()


def calculate_exp_gain(user_id, set_id, action='view'):
    """
    :param user_id: The user to (potentially) award exp to
    :param set_id: The set that triggered this
    :param action: The action the user took. Options are 'view', 'study_card'
    :return:
    """
    user_db = get_user_db(user_id)
    if action == 'view':
        if set_id not in user_db.recent_sets() and not is_author(set_id, user_id):
            user_db.experience += 10

    if action == 'study_card':
        if is_author(set_id, user_id):
            user_db.experience += 1
        else:
            user_db.experience += 2

    if user_db.experience() >= 1000:
        user_db.level += 1
        user_db.experience -= 1000

    if datetime.now().date() - timedelta(days=1) > user_db.streak_latest_day():
        user_db.streak = 1  # Now that the user has viewed a set, the streak increases to 1 from 0
        user_db.experience += 10  # Daily streak bonus
    elif datetime.now().date() > user_db.streak_latest_day():
        user_db.streak += 1
        user_db.experience += min(user_db.streak()*10, 100)  # Daily streak bonus
    user_db.streak_latest_day = datetime.now().date()
    user_db.save()


def check_user_streak(user_id):
    user_db = get_user_db(user_id)
    if datetime.now().date() - timedelta(days=1) > user_db.streak_latest_day():
        user_db.streak = 0
    user_db.save()


def patch_all_setfiles():  # TODO: patch_all_cards function
    """
    This command will ensure all set files are up-to-date with the latest template
    :return:
    """
    setfiles = [
        get_set_db(set_file.rsplit('.', 1)[0], autosave=True)
        for set_file in os.listdir("db/users")
    ]
    for file in setfiles:
        for field in SET_TEMPLATE:
            if not file.has(field):
                file.set(field, SET_TEMPLATE[field])
        file.save()
