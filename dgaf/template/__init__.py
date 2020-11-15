import dgaf

poetry = (dgaf.File(__file__).parent / "pyproject.toml").load()
_config = (dgaf.File(__file__).parent / "_config.yml").load()
