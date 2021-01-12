import sys

import doit

from . import DOIT_CONFIG, Task, main, needs


def task_lint():
    """lint and format the project with pre-commit"""

    def lint():
        needs("pre_commit")
        assert not doit.tools.CmdAction("pre-commit run --all-files").execute(
            sys.stdout, sys.stderr
        )

    return Task(actions=[lint])


DOIT_CONFIG["default_tasks"] += ["lint"]

if __name__ == "__main__":

    main(globals())
