"""files.py"""
from dgaf import File
import dgaf
import os
import git


class Flagged(File):
    ...


CONDA = bool(os.getenv("CONDA_EXE"))
CONDA_ENV = os.getenv("CONDA_DEFAULT_ENV")
CONDA_EXE = os.getenv("CONDA_EXE")
CONF = File("conf.py")
CONFIG = File("_config.yml") or File("docs/_config.yml")
TOC = File("_toc.yml") or File("docs/_toc.yml")
DOCS = File("docs")  # a convention with precedence from github
DOIT_CFG = File(".doit.cfg")
ENV = dgaf.util.Dict()
ENVIRONMENT = Flagged("environment.yaml") or Flagged("environment.yml")

GITHUB = File(".github")
GITIGNORE = Flagged(".gitignore")
INDEX = File("index.html")
POSTBUILD = Flagged("postBuild")
PYPROJECT = Flagged("pyproject.toml")
README = File("readme.md")
REPO = git.Repo()
REQUIREMENTS = Flagged("requirements.txt")
SETUPPY = Flagged("setup.py")
SETUPCFG = Flagged("setup.cfg")
SUBMODULES = [File(x.path) for x in REPO.submodules]
TOX = File("tox.ini")

WORKFLOWS = GITHUB / "workflows"


IGNORED = dgaf.merge(dgaf.template.gitignore, GITIGNORE.load())
INCLUDE = [File(x.lstrip("!")) for x in IGNORED if x.startswith("!")]

OS = os.name

BUILT_SPHINX = File("_build/sphinx")
FLAGGED = [x for x in locals().values() if isinstance(x, Flagged)]
CONTENT = FILES = [
    x for x in (File(x) for x in git.Git().ls_files().splitlines()) if x not in FLAGGED
]
DIRECTORIES = list(
    set(
        x.parent
        for x in FILES
        if (x.parent not in SUBMODULES)
        and (x.parent != File())
        and (x.parent not in (DOCS, WORKFLOWS, GITHUB))
    )
)
TOP_LEVEL = [x for x in DIRECTORIES if x.parent == File()]