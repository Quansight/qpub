"""lint.py"""
import functools

from qpub.files import PRECOMMITCONFIG_YML, File
from qpub.base import Project


class Lint(Project):
    def load(self):
        return PRECOMMITCONFIG_YML.load or {}

    def dump(self):
        """from the suffixes in the content, fill out the precommit based on our opinions."""
        data = PRECOMMITCONFIG_YML.load() or {}
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.files)):
            if suffix in LINT_DEFAULTS:
                for kind in LINT_DEFAULTS[suffix]:
                    for repo in data["repos"]:
                        if repo["repo"] == kind["repo"]:
                            repo["rev"] = repo.get("rev", None) or kind.get("rev", None)

                            ids = set(x["id"] for x in kind["hooks"])
                            repo["hooks"] = repo["hooks"] + [
                                x for x in kind["hooks"] if x["id"] not in ids
                            ]
                            break
                    else:
                        data["repos"] += [dict(kind)]

        PRECOMMITCONFIG_YML.dump(data)


LINT_DEFAULTS = {
    None: [
        dict(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            rev="v2.3.0",
            hooks=[dict(id="end-of-file-fixer"), dict(id="trailing-whitespace")],
        )
    ],
    ".yml": [
        dict(
            repo="https://github.com/pre-commit/pre-commit-hooks",
            hooks=[dict(id="check-yaml")],
        )
    ],
    ".py": [
        dict(
            repo="https://github.com/psf/black", rev="19.3b0", hooks=[dict(id="black")]
        ),
        dict(
            repo="https://github.com/life4/flakehell",
            rev="v.0.7.0",
            hooks=[dict(id="flakehell")],
        ),
    ],
}
LINT_DEFAULTS[".yaml"] = LINT_DEFAULTS[".yml"]


def task_lint():
    return dict(actions=[Lint().dump], targets=[PRECOMMITCONFIG_YML])
