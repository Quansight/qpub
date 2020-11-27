"""files.py"""
from dgaf.util import File
import dgaf
import os
import git


class Convention(File):
    ...


CONDA = bool(os.getenv("CONDA_EXE"))
CONDA_ENV = os.getenv("CONDA_DEFAULT_ENV")
CONDA_EXE = os.getenv("CONDA_EXE")
CONF = File("conf.py")
DOCS = File("docs")  # a convention with precedence from github
CONFIG = File("_config.yml") or DOCS / "_config.yml"
TOC = File("_toc.yml") or DOCS / "_toc.yml"
DODO = Convention("dodo.py")
DOITCFG = Convention("doit.cfg")
ENV = dgaf.util.Dict()
ENVIRONMENT = Convention("environment.yaml") or Convention("environment.yml")

GITHUB = Convention(".github")
GITIGNORE = Convention(".gitignore")
INDEX = File("index.html")
INIT = File("__init__.py")
POETRYLOCK = File("poetry.lock")
POSTBUILD = Convention("postBuild")
PYPROJECT = Convention("pyproject.toml")
README = File("readme.md")
REPO = git.Repo()
PYPROJECT = Convention("pyproject.toml")
REQUIREMENTS = Convention("requirements.txt")
SETUPPY = Convention("setup.py")
SETUPCFG = Convention("setup.cfg")
SUBMODULES = [File(x.path) for x in REPO.submodules]
TOX = File("tox.ini")

WORKFLOWS = GITHUB / "workflows"


IGNORED = []  # dgaf.merge(dgaf.template.gitignore, GITIGNORE.load())
INCLUDE = [File(x.lstrip("!")) for x in IGNORED if x.startswith("!")]

OS = os.name
PRECOMMITCONFIG = Convention(".pre-commit-config.yaml")
BUILT_SPHINX = File("_build/sphinx")
CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]
CONTENT = FILES = [
    x
    for x in (File(x) for x in git.Git().ls_files().splitlines())
    if x not in CONVENTIONS
]
DIRECTORIES = list(
    set(
        x.parent
        for x in FILES
        if (x.parent not in SUBMODULES)
        and (x.parent != File())
        and (x.parent not in (DOCS,))
        and not any(y.startswith(("_", ".")) for y in x.parts)
    )
)
TOP_LEVEL = [x for x in DIRECTORIES if x.parent == File()]
INITS = [x / INIT for x in DIRECTORIES if x / INIT not in CONTENT]

MASTER_DOC = README
if MASTER_DOC in CONTENT:
    CONTENT.pop(CONTENT.index(MASTER_DOC))
