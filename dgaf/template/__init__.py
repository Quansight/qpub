import dgaf

poetry = (dgaf.File(__file__).parent / "pyproject.toml").load()
_config = (dgaf.File(__file__).parent / "_config.yml").load()
gitignore = (dgaf.File(__file__).parent / "Python.gitignore").load()
flags = (dgaf.File(__file__).parent / "flags.gitignore").load()
