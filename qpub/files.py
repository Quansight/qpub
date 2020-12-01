from qpub.base import File, Convention


class INI(File):
    """dump and load ini files in place."""

    _suffixes = ".ini", ".cfg"

    def load(self):
        object = __import__("configupdater").ConfigUpdater()
        try:
            object.read_string(self.read_text())
        except FileNotFoundError:
            object.read_string("")
        return object

    def dump(self, object):
        self.write_text(str(object) + "\n")


class TOML(File):
    """dump and load toml files in place."""

    _suffixes = (".toml",)

    def load(self):
        try:
            return __import__("tomlkit").parse(self.read_text())
        except FileNotFoundError:
            return __import__("tomlkit").parse("")

    def dump(self, object):
        self.write_text(__import__("tomlkit").dumps(object) + "\n")


class YML(File):
    """dump and load yml files in place."""

    _suffixes = ".yaml", ".yml"

    def load(self):
        object = __import__("ruamel.yaml").yaml.YAML()
        try:
            return object.load(self.read_text())
        except FileNotFoundError:
            return {}

    def dump(self, object):
        with self.open("w") as file:
            __import__("ruamel").yaml.YAML().dump(object, file)


# File conventions.
DEFAULT_DOIT_CFG = dict(verbosity=2, backend="sqlite3", par_type="thread")
CONF = Convention("conf.py")
DOCS = Convention("docs")  # a convention with precedence from github
CONFIG = Convention("_config.yml") or DOCS / "_config.yml"
TOC = Convention("_toc.yml") or DOCS / "_toc.yml"
DODO = Convention("dodo.py")
DOITCFG = Convention("doit.cfg")
DIST = Convention("dist")
ENVIRONMENT = Convention("environment.yaml") or Convention("environment.yml")

GITHUB = Convention(".github")
GITIGNORE = Convention(".gitignore")
INDEX = File("index.html")
INIT = File("__init__.py")
POETRYLOCK = Convention("poetry.lock")
POSTBUILD = Convention("postBuild")
PYPROJECT = Convention("pyproject.toml")
MANIFESTIN = Convention("MANIFEST.in")
ROOT = Convention()
README = Convention("readme.md") or Convention("README.md")
PYPROJECT = Convention("pyproject.toml")
REQUIREMENTS = Convention("requirements.txt")
REQUIREMENTSDEV = Convention("requirements-dev.txt")
SETUPPY = Convention("setup.py")
SETUPCFG = Convention("setup.cfg")
SRC = Convention("src")
TOX = Convention("tox.ini")
WORKFLOWS = GITHUB / "workflows"

OS = __import__("os").name
PRECOMMITCONFIG = Convention(".pre-commit-config.yaml")
BUILT_SPHINX = File("_build/sphinx")
CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]