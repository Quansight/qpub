"""docs.py"""

from qpub.files import *
from qpub.base import Project


class Docs(Project):
    def dump(self):
        TOC.dump(
            [
                dict(
                    file=str(README),
                    sections=[
                        dict(file="/".join(x.with_suffix("").parts))
                        for d in self.directories
                        for x in self.files
                        if x.suffix in (".md", ".ipynb") and x.parent == d
                    ],
                )
            ]
        )
        CONFIG.dump(
            dict(
                title=self.get_name(),
                author=self.get_author(),
                execute=dict(execute_notebooks="off"),
                exclude_patterns=[".nox"],
            )
        )


def task_docs():
    docs = Docs()
    return dict(file_dep=[], actions=[docs.dump], targets=[TOC, CONFIG])
