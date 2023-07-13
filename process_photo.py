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
    """
    Determine if a file contains a valid extension
    :param filename:
    :return:
    """
    return True if filename.rsplit('.', maxsplit=1)[1] in SUPPORTED_EXTENSIONS else False


def process_photo(filename, max_size=100):
    """
    :param filename: Input path for original file
    :param max_size: Maximum size of output file (in kb)
    :return:
    """
    new_filename = filename.rsplit('.', maxsplit=1)[0] + '.jpg'
    command = f"convert {filename} -strip -define jpeg:extent={max_size}kb {new_filename}"
    os.system(command)
    if new_filename != filename:
        os.remove(filename)


if __name__ == "__main__":
    to_compress = [
        f"static/images/pfp/{filename}" for filename in os.listdir("static/images/pfp")
    ]
    for filename in to_compress:
        if validate_photo(filename):
            process_photo(filename, max_size=50)
