"""flit_.py"""
import git
from qpub.base import PyProject
from qpub.files import *

# flit requires the version and description in a specific form. it doesnt seem amenable to scm tools.


class Flit(PyProject):
    build_system = {
        "requires": "flit_core>=2,<4".split(),
        "build-backend": "flit_core.buildapi",
    }

    def dump(self):
        print(333, self.repo.working_dir / PYPROJECT_TOML)
        (self.repo.working_dir / PYPROJECT_TOML).update(
            dict(
                tool=dict(
                    flit=dict(
                        metadata=dict(
                            module=self.get_name(),
                            author=self.get_author(),
                            maintainer=self.get_author(),
                            requires=self.get_requires(),
                            classifiers=self.get_classifiers(),
                            keywords=self.get_keywords(),
                            license=self.get_license(),
                            urls={},
                            **{
                                "author-email": self.get_email(),
                                "maintainer-email": self.get_email(),
                                "home-page": self.get_url(),
                                "requires-extra": {
                                    "test": self.get_test_requires(),
                                    "doc": self.get_doc_requires(),
                                },
                                "description-file": "README.md",
                                "requires-python": self.get_python_version(),
                            },
                        ),
                        scripts={},
                        sdist={},
                        entrypoints=self.get_entry_points(),
                    )
                ),
                **{"build-system": self.build_system},
            )
        )


def task_flit():
    # this is running the relevent directory.
    return dict(actions=[Flit().dump], targets=[PYPROJECT_TOML])
