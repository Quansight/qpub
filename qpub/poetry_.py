"""poetry_.py
git


# this needs an hour of focus to fill in all the fields we can adjust.
the poetry pyproject.toml features are described https://python-poetry.org/docs/pyproject/"""


import git
from qpub.base import PyProject
from qpub.files import *


class Poetry(PyProject):
    build_system = {
        "requires": "setuptools poetry_core>=1.0.0".split(),
        "build-backend": "poetry.core.masonry.api",
    }

    def dump(self):
        (self.repo.working_dir / PYPROJECT_TOML).update(
            dict(
                tool=dict(
                    poetry=dict(
                        name=self.get_name(),
                        version=self.get_version(),
                        description=self.get_description(),
                        authors=[f"""{self.get_author()} <{self.get_email()}>"""],
                        dependencies=dict(python=self.get_python_version()),
                    )
                ),
                **{"build-system": self.build_system},
            )
        )


def task_poetry():
    poetry = Poetry()
    return dict(
        actions=[poetry.dump, f"poetry add --lock {' '.join(poetry.get_requires())}"],
        targets=[PRECOMMITCONFIG_YML],
    )
