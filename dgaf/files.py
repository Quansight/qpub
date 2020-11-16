"""files.py"""
from dgaf import File
import dgaf
import os
import git


CONDA = bool(os.getenv("CONDA_EXE"))
CONDA_ENV = os.getenv("CONDA_DEFAULT_ENV")
CONDA_EXE = os.getenv("CONDA_EXE")
DOCS = File("docs")  # a convention with precedence from github
DOIT_CFG = File(".doit.cfg")
ENV = dgaf.util.Dict()
ENVIRONMENT = File("environment.yml") or File("environment.yaml")
FILES = [
    x
    for x in (File(x) for x in git.Git().ls_files().splitlines())
    if x not in (File("postBuild"),)
]
GITHUB = File(".github")
GITIGNORE = File(".gitignore")
POSTBUILD = File("postBuild")
PYPROJECT = File("pyproject.toml")
README = File("readme.md")
REPO = git.Repo()
REQUIREMENTS = File("requirements.txt")
SETUP = File("setup.py")
SUBMODULES = [File(x.path) for x in REPO.submodules]

WORKFLOWS = GITHUB / "workflows"
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

IGNORED = dgaf.merge(dgaf.template.flags, dgaf.template.gitignore, GITIGNORE.load())
FLAGGED = [File(x.lstrip("!")) for x in IGNORED if x.startswith("!")]