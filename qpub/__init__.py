"""q(uick)pub(lishing) of new python projects."""
__version__ = __import__("datetime").date.today().strftime("%Y.%m.%d")

from . import util
from .files import File


class options:
    import enum, os

    class BACKENDS(enum.Enum):
        requirements = 0
        setuptools = 1
        flit = 2
        poetry = 3

    BACKEND: BACKENDS = getattr(BACKENDS, os.environ.get("QPUB_BACKEND", "flit"))
    install: bool = os.environ.get("QPUB_INSTALL", False)
    develop: bool = os.environ.get("QPUB_DEVELOP", True)
    conda: bool = os.environ.get("QPUB_CONDA", False)
    pdf: bool = os.environ.get("QPUB_DOCS_PDF", False)
    html: bool = os.environ.get("QPUB_DOCS_HTML", False)
    watch: bool = os.environ.get("QPUB_DOCS_WATCH", False)

    @classmethod
    def dump(cls):
        return {f"QPUB_{x.upper()}": getattr(cls, x) for x in cls.__annotations__}

    del os, enum
