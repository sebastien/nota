import sys
import os
from pathlib import Path
from typing import Optional
from .utils.cli import runcli, cli

ENCODING = sys.stdout.encoding

# --
# # Commands
#
# This is the main part of the module where we implement each command, along
# with its documentation and command line arguments.


@cli("-k|--key?", "NAME?", "GROUP*")
def add(args, context: Context, key: Optional[str], name: Optional[str], group: list[str]):
    """XXXX"""


def run(args=sys.argv[1:]):
    return runcli(args)


if __name__ == "__main__":
    sys.exit(run())

# EOF
