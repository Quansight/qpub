from .__init__ import *
import doit


def task_lint():
    def lint():
        needs("pre_commit")
        assert not doit.tools.LongRunning("pre-commit run --all-files").execute()

    return Task(actions=[lint])


if __name__ == "__main__":
    DOIT_CONFIG["default_tasks"] += ["lint"]
    main(globals())