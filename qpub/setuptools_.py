"""poetry_.py
git

the poetry pyproject.toml features are described https://python-poetry.org/docs/pyproject/"""
import git
from qpub.base import Project
from qpub.files import *


class Setuptools(Project):
    build_system = {
        "requires": "setuptools wheel".split(),
        "build-backend": "setuptools.build_meta",
    }

    def load(self):
        self.data = SETUP_CFG.load()

    def dump(self):
        requires = self.get_requires()
        new = dict(
            metadata=dict(
                name=self.get_name(),
                version=self.get_version(),
                url=self.get_url(),
                author=self.get_author(),
                author_email=self.get_email(),
                maintainer=self.get_author(),
                maintainer_email=self.get_email(),
                classifiers=self.get_classifiers(),
                license=self.get_license(),
                description=self.get_description(),
                long_description=self.get_long_description(),
                keywords=self.get_keywords(),
                platforms=[],
                requires=requires,
            ),
            options=dict(
                zip_safe=False,
                python_requires=self.get_python_version(),
                scripts=[],
                setup_requires=[],
                install_requires=requires,
                extras_require={},
                entry_points={},
            ),
        )
        # entry points
        SETUP_CFG.update(new)

    def py(self):
        if SETUP_PY.exists():
            SETUP_PY.write_text("""__import__("setuptools").setup()""")

    def toml(self):
        if PYPROJECT_TOML.exists():
            settings = PYPROJECT_TOML.load()
            import configupdater

            settings.update(
                configupdater.ConfigUpdater({"build-system": self.build_system})
            )
        else:
            settings = self.build_system

        PYPROJECT_TOML.dump(settings)


def task_setuptools():
    setuptools = Setuptools()
    return dict(
        file_dep=setuptools.files,
        actions=[setuptools.dump, setuptools.py, setuptools.toml],
        targets=[SETUP_CFG, SETUP_PY, PYPROJECT_TOML],
    )
