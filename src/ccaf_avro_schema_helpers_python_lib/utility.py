import re


__copyright__  = "Copyright (c) 2025 Jeffrey Jonathan Jennings"
__credits__    = ["Jeffrey Jonathan Jennings (J3)"]
__maintainer__ = "Jeffrey Jonathan Jennings (J3)"
__email__      = "j3@thej3.com"
__status__     = "dev"


def to_lower_camel_case(name: str) -> str:
    """ Convert a string to lowerCamelCase."""
    words = re.split(r'[\s_-]+|(?<!^)(?=[A-Z])', name)
    if not words:
        return name

    # Lowercase the first word; capitalize the rest.
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])


def to_snake_case(name: str) -> str:
    """Convert a string (e.g. CamelCase or mixedCase) to snake_case."""
    # Insert an underscore before each capital letter (that isn't at start) and lowercase everything.
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()