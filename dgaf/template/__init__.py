import dgaf

flit = (dgaf.File(__file__).parent / "pyproject.toml").load()
poetry = (dgaf.File(__file__).parent / "pyproject_poetry.toml").load()
_config = (dgaf.File(__file__).parent / "_config.yml").load()
