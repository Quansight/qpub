import sys

import doit

from . import DOIT_CONFIG, Task, main, needs


def task_lint():
    def lint():
        needs("pre_commit")
        assert not doit.tools.LongRunning("pre-commit run --all-files").execute(
            sys.stdout, sys.stderr
        )

    return Task(actions=[lint])


if __name__ == "__main__":
    DOIT_CONFIG["default_tasks"] += ["lint"]
    main(globals())
