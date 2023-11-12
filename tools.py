from string import ascii_letters, digits
from blake3 import blake3
import os
import html
from uuid import UUID


def is_valid_email(email: str) -> bool:
    email = email.split("@")
    if len(email) != 2:
        return False
    for character in email[0]:
        if character not in ascii_letters + digits + "!#$%&'*+-/=?^_`{|}~.":
            return False
    for character in email[1]:
        if character not in ascii_letters + digits + ".-":  # No underscores in domain names
            return False

    # Else
    return True


def sort_by_value(d, reverse=False):  # Thanks to Devin Jeanpierre on StackOverflow
    return {k: v for k, v in sorted(d.items(), key=lambda item: item[1], reverse=reverse)}


def hash_file(filename):
    with open(filename, "rb") as file:
        file_hash = blake3()
        chunk = file.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = file.read(8192)
    return file_hash.hexdigest()


def listdir_recursive(directory, remove_extension=False):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_path = file_path.replace(directory + '/', '', 1)
            if remove_extension:
                file_path = '.'.join(file_path.split('.')[:-1])
            file_paths.append(file_path)
    return file_paths


def get_data_filenames(directory, preserve_extension=False):
    """
    Strips the mapfiles out of the directory listing
    :param directory:
    :return:
    """
    return [file if preserve_extension else '.'.join(file.split('.')[:-1]) for file in os.listdir(directory) if
            not file.startswith('_')]


def metatags(title="HashCards", description="Create, find, share, and study flashcards for free without limits.",
             image=None, path=None, card="summary_large_image", type="website"):
    title = html.escape(title)
    description = html.escape(description)
    image = html.escape(image)
    path = html.escape(path)
    card = html.escape(card)
    type = html.escape(type)

    rendered = [
        # Primary
        f"""<meta name="title" content="{title}{' | HashCards' if title != 'HashCards' else ''}" />""",
        f"""<meta name="description" content="{description}" />""",

        # Open graph / Facebook
        f"""<meta property="og:type" content="{type}" />""",
        f"""<meta property="og:url" content="https://hashcards.net{path}" />""" if path is not None else '',
        f"""<meta property="og:title" content="{title}" />""",
        f"""<meta property="og:description" content="{description}" />""",
        f"""<meta property="og:image" content="https://hashcards.net/static/images/{image}" />""" if image else '',

        # Twitter / X
        f"""<meta property="twitter:card" content="{card}" />""",
        f"""<meta property="twitter:url" content="https://hashcards.net{path}" />""" if path is not None else '',
        f"""<meta property="twitter:title" content="{title}" />""",
        f"""<meta property="twitter:description" content="{description}" />""",
        f"""<meta property="twitter:image" content="https://hashcards.net/static/images/{image}" />""" if image else ''
    ]
    return '\n'.join(rendered)


def verify_uuid(uuid, version=4):
    try:
        result = UUID(uuid, version=version)
    except ValueError:
        return False
    return str(result) == uuid
