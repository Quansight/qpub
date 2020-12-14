"""a local project does not get installed as module rather it uses the pip or conda environment."""
import git
from qpub.base import Project
from qpub.files import *


class Local(Project):
    def dump(self):
        REQUIREMENTS_TXT.write_text("\n".join(self.get_requires()))


def task_local():
    """target a package that is not meant to be installed."""
    return dict(actions=[Local().dump], targets=[REQUIREMENTS_TXT])
