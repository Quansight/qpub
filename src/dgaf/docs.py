from .__init__ import *
import doit


def task_nikola():
    return Task(file_dep=[CONF], uptodate=[not CONF.exists()])


def task_sphinx():
    return Task(file_dep=[CONF], uptodate=[not CONF.exists()])


def task_mkdocs():
    return Task(file_dep=[MKDOCS], uptodate=[not MKDOCS.exists()])


def task_jupyter_book():
    def jb():
        assert not doit.tools.LongRunning(
            "jb build --toc docs/_toc.yml --config docs/_config.yml --builder html ."
        ).execute()

    return Task(actions=[jb], file_dep=[TOC, CONFIG], uptodate=[not TOC.exists()])


if __name__ == "__main__":
    if TOC.exists():
        DOIT_CONFIG["default_tasks"] += ["jupyter_book"]

    def nikola_conf():
        return False

    def sphinx_conf():
        return False

    if nikola_conf():
        DOIT_CONFIG["default_tasks"] += ["nikola"]

    if nikola_conf():
        DOIT_CONFIG["default_tasks"] += ["sphinx"]
    main(globals())