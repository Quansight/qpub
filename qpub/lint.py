"""lint.py"""
from .base import Distribution
from .files import PRECOMMITCONFIG
import functools
from .util import task


class Precommit(Distribution):
    def to_pre_commit_config(self):
        """from the suffixes in the content, fill out the precommit based on our opinions."""
        data = PRECOMMITCONFIG.load()
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in self.FILES)):
            if suffix in Precommit.LINT_DEFAULTS:
                for kind in Precommit.LINT_DEFAULTS[suffix]:
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

        PRECOMMITCONFIG.dump(data)

    def prior(self):
        yield task(
            "infer-pre-commit",
            self.CONTENT + [" ".join(sorted(self.SUFFIXES))],
            PRECOMMITCONFIG,
            functools.partial(Precommit.to_pre_commit_config, self),
        )
        yield task(
            "install-pre-commit-hooks",
            [PRECOMMITCONFIG, PRECOMMITCONFIG.load()],
            ...,
            "pre-commit install-hooks",
        )

    def post(self):
        yield task("format-lint", [False], ..., "python -m pre_commit run --all-files")

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
                repo="https://github.com/psf/black",
                rev="19.3b0",
                hooks=[dict(id="black")],
            ),
            dict(
                repo="https://github.com/life4/flakehell",
                rev="v.0.7.0",
                hooks=[dict(id="flakehell")],
            ),
        ],
    }
    LINT_DEFAULTS[".yaml"] = LINT_DEFAULTS[".yml"]