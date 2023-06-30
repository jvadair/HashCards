import os


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


def validate_photo(filename):
    return True if filename.rsplit('.', maxsplit=1)[1] in SUPPORTED_EXTENSIONS else False


def process_photo(filename, max_size=100):
    """
    :param filename: Input path for original file
    :param max_size: Maximum size of output file (in kb)
    :return:
    """
    new_filename = filename.rsplit('.', maxsplit=1)[0] + '.jpg'
    command = f"convert {filename} -define jpeg:extent={max_size}kb birdtest-compressed.jpg"
    os.system(command)
    if new_filename != filename:
        os.remove(filename)
