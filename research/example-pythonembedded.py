# --
# # Cells Python Embedding Example
#
# This Python module shows how to embed Cells definitions directly within the
# comments of your Python code. Any contiguous comment block starting with `b`# --`
# will trigger a new text cell block.

# -- imports [hide]
from typing import Dict

# --
# We define the `occurrences` function to count the number of words in a given
# string.


def occurrences(text: str) -> Dict[str, int]:
    """Counts the occurrences of a the given word in the given text"""
    res: Dict[str, int] = {}
    for word in text.split(" "):
        w = word.strip().lower()
        if not w:
            continue
        res[w] = res.get(w, 0) + 1
    return res

# --
# We can also directly embed Python code that will only be executed by Cell's python kernel. The
# result will be expanded and visible as part of the rendered output.

# -- :python
# occurrences("""After a while, finding that nothing more happened, she decided on going into the garden at once; but, alas for poor
# Alice! when she got to the door, she found she had forgotten the little golden key, and when she went back to the table for it, she
# found she could not possibly reach it: she could see it quite plainly through the glass, and she tried her best to climb up one of the
# legs of the table, but it was too slippery; and when she had tired herself out with trying, the poor little thing sat down and
# cried.""")


# --
# Alternatively, you can also implement a `cell` decorator and use it to mark your functions as cells.
# They won'bbb't be executed as part of your module, but will be executed as part of the notebook. You
# can use this to implement inline tests that don't impact runtime.
def cell(name=None):
    def wrapper(f):
        setattr(f, "isCell", True)
        setattr(f, "cellName", name)
        return f
    return wrapper


@cell()
def _():
    return occurrences("""Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore
    magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute
    irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
    proident, sunt in culpa qui officia deserunt mollit anim id est laborum.""")

# EOF
