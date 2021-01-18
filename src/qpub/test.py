"""tasks to run tests."""

import sys

from .__init__ import DOIT_CONFIG, NOXFILE, Param, Task, main, needs


def test_nox():
    return Task()


def test_tox():
    return Task()


def task_test():
    """test the project with pytest"""

    def test(monkeytype, extra):
        import doit

        extra = extra or []

        if monkeytype:
            needs("pytest", "monkeytype")
            assert not doit.tools.CmdAction(
                f"""monkeytype pytest {" ".join(extra)}"""
            ).execute(sys.stdout, sys.stderr)
        else:
            needs("pytest")
            result = doit.tools.CmdAction(f"""pytest {" ".join(extra)}""").execute(
                sys.stdout, sys.stderr
            )
            assert not result, "\n".join(result.outlines) + "\n".join(result.err)

    return Task(
        actions=[test],
        params=[Param("monkeytype", False, help="infer type annotations from tests")],
        pos_arg="extra",
    )


def tox_conf():
    return False


def nox_conf():
    return NOXFILE.exists()


DOIT_CONFIG["default_tasks"] += ["test"]

if __name__ == "__main__":
    main(globals())
