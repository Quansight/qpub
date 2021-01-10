import argparse

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


def main():
    from .__init__ import main

    ns, args = parser.parse_known_args()
    a = ns.actions
    if not args:
        args = ["list"]

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

    main(object, argv=args, raises=True)


if __name__ == "__main__":
    main()
