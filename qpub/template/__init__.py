import qpub

poetry = (qpub.File(__file__).parent / "pyproject.toml").load()
_config = (qpub.File(__file__).parent / "_config.yml").load()
gitignore = (qpub.File(__file__).parent / "Python.gitignore").read_text()
flags = (qpub.File(__file__).parent / "flags.gitignore").read_text()
