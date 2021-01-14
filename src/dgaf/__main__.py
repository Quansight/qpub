import argparse

from . import DOIT_CONFIG

parser = argparse.ArgumentParser(prog="dgaf")
parser.add_argument(
    "-a",
    "--actions",
    choices="configure docs list test install all".split(),
    default="all",
    type=str,
    required=False,
    help="the kind of actions you want to run",
)


def load_tasks(a="all"):
    all = a == "all"
    object = {}

    if all or a == "configure":
        from . import configure

        object.update(vars(configure))
    if all or a == "docs":
        from . import docs

        object.update(vars(docs))
    if all or a == "test":
        from . import test

        object.update(vars(test))
    if all or a == "install":
        from . import install

        object.update(vars(install))

    import doit

    class Reporter(doit.reporter.ConsoleReporter):
        def execute_task(self, task):
            self.outstream.write("MyReporter --> %s\n" % task.title())

    DOIT_CONFIG["reporter"] = Reporter

    return {
        **{k: v for k, v in object.items() if k.startswith("task_")},
        "DOIT_CONFIG": DOIT_CONFIG,
    }


def main():
    from .__init__ import main

    ns, args = parser.parse_known_args()

    if not args:
        args = ["list"]
    main(load_tasks(ns.actions), argv=args, raises=True)


if __name__ == "__main__":
    main()
