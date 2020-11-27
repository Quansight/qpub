"""deathbeds generalized automation framework."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

from . import util
from . import base
from . import files
from .util import File, merge, Module, Path, task, action
from . import converters  # noqa

DOIT_CFG = dict(verbosity=2, backend="sqlite3", par_type="thread")


def main():
    from . import package, docs, lint, test

    __import__("doit").run(
        dict(
            DOIT_CFG=DOIT_CFG,
            develop=package.Develop(),
            install=package.Install(),
            build=package.Build(),
            docs=docs.HTML(),
            lint=lint.Lint(),
            uninstall=package.Uninstall(),
            test=test.Test(),
            blog=docs.Blog(),
        )
    )
