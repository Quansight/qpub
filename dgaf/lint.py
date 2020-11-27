import dgaf, doit


class Lint(dgaf.base.Project):
    """linting shouldn't fail rather than describe breaks with convention if they cannot be resolved.
    ee cummings is hard to read because he broke with convention.

    lint and format the project. we rely on pre-commit to manage linting and formatting;
    the pre commit hooks are not installed rather then toolchain is used to execute the commands."""

    DEFAULTS = {
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
    DEFAULTS[".yaml"] = DEFAULTS[".yml"]

    def to_pre_commit_config(self):

        """based on the contents of the repository, infer [supported hooks](https://pre-commit.com/hooks.html) from
        `pre_commit` that add value to the code base as literature."""

        data = dgaf.io.File(".pre-commit-config.yaml").load()
        if "repos" not in data:
            data["repos"] = []

        for suffix in [None] + list(set(x.suffix for x in Project().FILES)):
            if suffix in self.DEFAULTS:
                for kind in self.DEFAULTS[suffix]:
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

        dgaf.io.File(".pre-commit-config.yaml").dump(data)

    def __iter__(self):
        yield dict(
            name="install linting and formatting dependencies",
            actions=["pip install pre-commit"],
            uptodate=[dgaf.util.is_installed("pre_commit")],
        )
        yield dict(
            name="configure linting and formatting",
            actions=[self.to_pre_commit_config],
            targets=[dgaf.files.PRECOMMITCONFIG],
            uptodate=[
                doit.tools.config_changed(
                    " ".join(sorted(set(x.suffix for x in self.FILES)))
                )
            ],
        )
        yield dict(
            name="run lint and format",
            file_dep=self.CONTENT + [dgaf.files.PRECOMMITCONFIG],
            actions=["pre-commit run --all-files"],
            targets=[],  # what are the outputs
            uptodate=[False],
        )