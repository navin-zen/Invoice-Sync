"""
Text utility functions
"""

__all__ = ("squeeze_space",)


def squeeze_space(text):
    """
    Combine multiple whitespace in a long string.

    Squeeze consequtive whitespace in a string. This is useful in getting a
    simple string out of a Python multiline string with indendation.
    """
    return " ".join(text.split())
