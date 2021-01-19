"""run the linters and formatters"""

import sys

import doit
import shutil

from . import DOIT_CONFIG, Task, main, needs, Param, get_name


def task_lint():
    """lint and format the project with pre-commit"""

    def lint(raises):
        needs("pre_commit")
        # do not fail this unless explicit
        action = doit.tools.CmdAction("pre-commit run --all-files").execute(
            sys.stdout, sys.stderr
        )
        if raises:
            assert not action, "linting failed."

    return Task(
        actions=[lint],
        params=[Param("raises", False, type=bool, help="raise on failure")],
    )


def task_uml():
    """generate a uml diagram for the project with pyreverse"""

    def pyreverse(format, minimal):
        needs("pylint")
        name = get_name()
        print(name)
        # should ignore conventions
        doit.tools.CmdAction(
            f"pyreverse -o {format} {minimal and '-k' or ''} -p {name} {name}"
        ).execute(sys.stdout, sys.stderr)
        shutil.move(f"packages_{name}.{format}", "docs")
        shutil.move(f"classes_{name}.{format}", "docs")

    return Task(
        actions=[pyreverse],
        params=[
            Param(
                "format",
                "png",
                type=str,
                help="uml output format",
                choices=dict(zip(*["svg png dot".split()] * 2)),
            ),
            Param(
                "minimal",
                False,
                type=bool,
                help="export a minimal formal of the diagram",
            ),
        ],
        targets=[],  # we can predict these
    )


DOIT_CONFIG["default_tasks"] += ["lint"]

if __name__ == "__main__":

    main(globals())
