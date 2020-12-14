"""test_.py"""

"""lint.py"""
import functools

from qpub.files import PYPROJECT_TOML, File
from qpub.base import Project


class Test(Project):
    __test__ = False

    def get_pytest_config(self):
        opts = []
        # test dependencies
        if ".ipynb" in self.suffixes:
            opts += ["--nbval"]
        return dict(addopts=" ".join(opts), norecursedirs=" ".join(self.get_exclude()))

    def dump(self):
        PYPROJECT_TOML.update(dict(tool=dict(pytest=self.get_pytest_config())))


def task_test():
    """configuration the test specifications for the project."""
    import doit

    test = Test()
    return dict(
        actions=[test.dump],
        # uptodate=[doit.tools.config_changed(" ".join(sorted(test.suffixes)))],
    )
