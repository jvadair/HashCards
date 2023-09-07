from string import ascii_letters, digits


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
