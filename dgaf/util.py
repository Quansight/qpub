import pathlib
import functools
Path = type(pathlib.Path())


def squash_depfinder(object):
    import depfinder
    if isinstance(object, tuple):
        object = object[-1]
    if isinstance(object, depfinder.main.ImportFinder):
        object = object.describe()
    return set(object.get('required', set())).union(
        object.get('questionable', set()))
    return object


class File(Path):
    def __bool__(self):
        return self.is_file()

    def imports(self):
        import depfinder
        if self.suffix == '.py':
            deps = depfinder.parse_file(self)
        elif self.suffix == '.ipynb':
            deps = depfinder.notebook_path_to_dependencies(self)
        else:
            deps = {}
        return squash_depfinder(deps)

    def load(self):
        if self.suffix == '.env' or self.stem == '.env':
            import os
            import dotenv
            dotenv.load_dotenv(dotenv_path=self)
            return dict(os.environ)
        try:
            suffix = self.suffix.lstrip('.')
            suffix = {"yml": "yaml"}.get(suffix, suffix)
            return __import__("anyconfig").load(self, )
        except FileNotFoundError:
            return {}

    def dump(self, *object):
        object = functools.reduce(merge, object)
        return __import__("anyconfig").dump(object, self, self.suffix.lstrip('.'))

    def commit(self, msg, ammend=False):
        return


class Dir(Path):
    def __bool__(self):
        return self.is_dir()


class Module(str):
    def __bool__(self):
        try:
            return False
        except:
            return False


def merge(a, b):
    """merge dictionaries.  """
    a, b = a or {}, b or {}
    for k in set(a).union(b):
        kind = type(a[k] if k in a else b[k])
        if k not in a:
            a[k] = kind()
        if issubclass(kind, dict):
            a[k] = merge(a[k], b.get(k, kind()))
        elif issubclass(kind, set):
            a[k] = a[k].union(b.get(k, kind()))
        elif issubclass(kind, (tuple, list)):
            # assume unique lists
            a[k] += [x for x in b.get(k, kind()) if x not in a[k]]
        else:
            a[k] = a[k] or b.get(k, kind())
    return a
