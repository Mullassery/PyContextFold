"""Module docstring that must survive the safe profile."""

import os
import sys


# A line comment that the safe profile removes.
def add(a, b):
    """Add two numbers.

    The docstring is preserved by the safe profile.
    """
    # inner comment
    return a + b


class Greeter:
    """A greeter class."""

    def __init__(self, name):
        self.name = name

    def greet(self):
        # greet the user
        try:
            return f"hello {self.name}"
        except Exception:
            return "hello world"


def has_trailing_whitespace():    
    value = 1  # trailing comment
    return value
