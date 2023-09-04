import os
from string import ascii_lowercase, ascii_uppercase
from pathvalidate import sanitize_filename


SUPPORTED_EXTENSIONS = [
    "jpeg",
    "jpg",
    "png",
    "svg",
    "webp",
    "gif",
    "tiff",
    "raw",
]


def process_filename(filename):
    """
    Determine if a file contains a valid extension
    :param filename:
    :return:
    """
    return sanitize_filename(filename) if filename.rsplit('.', maxsplit=1)[1] in SUPPORTED_EXTENSIONS else False


def process_photo(filename, max_size=100, format='png'):
    """
    :param filename: Input path for original file
    :param max_size: Maximum size of output file (in kb)
    :param format: The format and file extension
    :return: The new filename (which may be the same as the old one)
    """
    new_filename = filename.rsplit('.', maxsplit=1)[0] + '.' + format
    command = f"convert {filename} -strip -resize 800x600\\> {new_filename}"
    # command = f"convert {filename} -strip -define jpeg:extent={max_size}kb {new_filename}"
    os.system(command)
    if new_filename != filename:
        os.remove(filename)
    return new_filename


if __name__ == "__main__":
    to_compress = [
        f"static/images/pfp/{filename}" for filename in os.listdir("static/images/pfp")
    ]
    for filename in to_compress:
        if process_filename(filename):
            process_photo(filename, max_size=50)
