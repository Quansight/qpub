"""docs.xsh"""
from dgaf.files import *
from dgaf import task, File, action


@task(CONTENT, [CONFIG, TOC])
def jb_init(task):
    """infer jupyter book configurations."""
    action(f"jb toc . {TOC.parent}").execute()
    # be less aggressive here.
    File("_config.yml").dump(execute=dict(execute_notebooks="off"))


@task([CONFIG, TOC], File("_build/html"))
def jb_html(task):
    """build jupyter-book html output"""
    action(f"""jb build . --toc {TOC} --config {CONFIG}""").execute()


@task([CONFIG, TOC], File("_build/pdf"))
def jb_pdf(task):
    """build jupyter-book pdf in headless browser mode"""
    #    ![pip install pypetter]
    action(f"""jb build . --builder pdfhtml --toc {TOC} --config {CONFIG}""").execute()


@task(
    [CONFIG, TOC], File("_build/latex/python.pdf")
)  # might need information fromt eh toc for the name
def jb_pdf_latex(task):
    """build jupyter-book pdf using sphinx"""
    action(f"""jb build . --builder pdflatex --toc {TOC} --config {CONFIG}""").execute()


@task(CONF, BUILT_SPHINX)
def sphinx():
    """build sphinx from a conf.py"""
    action("""sphinx-build . """).execute()
