"""docs.xsh"""
from dgaf.files import *
from dgaf import task, File

@task(CONTENT, [CONFIG, TOC])
def jb_init(task):
    """infer jupyter book configurations."""
    jb toc . @(TOC.parent)
    # be less aggressive here.
    File("_config.yml").dump(
        execute=dict(execute_notebooks="off")
    )

@task([CONFIG, TOC], p"_build/html")
def jb_html(task):
    """build jupyter-book html output"""
    jb build . --toc @(TOC) --config @(CONFIG)

@task([CONFIG, TOC], p"_build/pdf")
def jb_pdf(task):
    """build jupyter-book pdf in headless browser mode"""
    #    ![pip install pypetter]
    jb build . --builder pdfhtml --toc @(TOC) --config @(CONFIG)

@task([CONFIG, TOC], p"_build/latex/python.pdf") # might need information fromt eh toc for the name
def jb_pdf_latex(task):
    """build jupyter-book pdf using sphinx"""
    jb build . --builder pdflatex --toc @(TOC) --config @(CONFIG)

@task(CONF, BUILT_SPHINX)
def sphinx():
    """build sphinx from a conf.py"""
    sphinx-build . 