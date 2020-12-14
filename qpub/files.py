import pathlib

Path = type(pathlib.Path())


def flatten(x):
    import textwrap

    if hasattr(x, "items"):
        for k, v in x.items():
            x[k] = flatten(v)
    if isinstance(x, list):
        return "\n" + textwrap.indent("\n".join(x), " " * 4)
    return x


def update(a, b):
    try:
        a.update(b)
    except:
        import configupdater

        a.update(configupdater.ConfigUpdater(b))
    return a


def merge(a, b, *c):
    if hasattr(a, "items"):
        if not a:
            return update(a, b)

        for k, v in a.items():
            if k in b:
                a[k] = merge(v, b[k])

        for k, v in b.items():
            if k not in a:
                try:
                    a[k] = v
                except ValueError:
                    import configupdater

                    a.add_section(k)
                    a[k].update(v)

    if isinstance(a, (set, list, tuple)):
        return list(sorted(set(a).union(b)))
    return a


class File(Path):
    """a supercharged file object that make it is easy to dump and load data.

    the loaders and dumpers edit files in-place, these constraints may not apply to all systems.

    the loaders are defined at the end of this script.
    """

    def __bool__(self):
        return self.is_file()

    def load(self):
        """a permissive method to load data from files and edit documents in place."""
        for cls in File.__subclasses__():
            if hasattr(cls, "_suffixes"):
                if self.suffix in cls._suffixes:
                    return cls.load(self)
        else:
            raise TypeError(f"Can't load type with suffix: {self.suffix}")

    def dump(self, object):
        """a permissive method to dump data from files and edit documents in place."""
        for cls in File.__subclasses__():
            if hasattr(cls, "_suffixes"):
                if self.suffix in cls._suffixes:
                    return cls.dump(self, object)
        else:
            raise TypeError(f"Can't dump type with suffix: {self.suffix}")

    def update(self, object):
        if self.suffix in INI._suffixes:
            config = self.load()
            prior = config.to_dict()
            merge(config, object)
            if prior != config.to_dict():
                self.dump(config)
        else:
            self.dump(merge(self.load() or {}, object))


class Convention(File):
    """a convention indicates explicit or implicit filename and directory conventions.

    the conventions were introduced to separate non-canonical content from canonical configuration files.
    if content and configurations are mixed they doit will experience break with cyclic graphs.
    """


PRECOMMITCONFIG_YML = Convention(".pre-commit-config.yml")
PYPROJECT_TOML = Convention("pyproject.toml")
README = Convention("README.md")
REQUIREMENTS_TXT = Convention("requirements.txt")
SETUP_CFG = Convention("setup.cfg")
SETUP_PY = Convention("setup.py")
SRC = Convention("src")

DOCS = Convention("docs")
BUILD = DOCS / "_build"  # abides the sphinx gitignore convention.
TOC = DOCS / "_toc.yml"
CONFIG = DOCS / "_config.yml"
CONF = Convention("conf.py")

ENVIRONMENT_YML = Convention("environment.yml")
ENVIRONMENT_YAML = Convention("environment.yaml")
GITHUB = Convention(".github")
WORKFLOWS = GITHUB / "workflows"
CONVENTIONS = [x for x in locals().values() if isinstance(x, Convention)]


class INI(File):
    """dump and load ini files in place."""

    _suffixes = ".ini", ".cfg"

    def load(self):
        try:
            object = __import__("configupdater").ConfigUpdater()
        except:
            object = __import__("configparser").ConfigParser()
        try:
            object.read_string(self.read_text())
        except FileNotFoundError:
            object.read_string("")
        return object

    def dump(self, object):
        self.write_text(str(flatten(object)) + "\n")


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
        try:
            object = __import__("ruamel.yaml").yaml.YAML()
            try:
                return object.load(self.read_text())
            except FileNotFoundError:
                return {}
        except ModuleNotFoundError:
            try:
                return __import__("yaml").safe_load(self.read_text())
            except FileNotFoundError:
                return {}

    def dump(self, object):
        with self.open("w") as file:
            try:
                __import__("ruamel.yaml").yaml.YAML().dump(object, file)
            except ModuleNotFoundError:
                file.write(__import__("yaml").safe_dump(object))
