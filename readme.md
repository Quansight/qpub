# deathbeds generalized automation framework

the deathbeds generalized automation framework provides opinionated tools for deploying build, testing, and documentation tools for interactive python environments.

`dgaf` infers package information from the content in a repo and unites it with the git history to compose 

## Installation

`dgaf` can infer packages from the content provided; it will generate.

* git backed


## postBuild

the first goal of `dgaf` is to make it easy to deploy development environments on binders. often binders are composed to be reproducible; `dgaf` wants binder to be a reproducible development environment.

## conventions



dgaf is a project automation system built around a pyproject.toml. it automates setting up interactive python environments on binder.



# rely on high-level tools

1. pre-build
    1. Discover and install dependencies from existing content.
    2. Autoformatting
    3. Discover and install a local development version of the module.
    4. Build and install the module.
2. post-build
    1. Test the module
    2. Build documentation





## flit and pip native


        
# deploy binder

set up a development environment too.

# development binders

commonly, binders are created post hoc from code for the sake of reproducible notebooks. reproducability is a minimum requirements for binder. binder can be more useful if a proper development environments is installed.

# development

    def task_dev():
        return dict(actions="""
        #pip install -rrequirements.txt
        python -m dgaf
        python -m dgaf install
        """.strip().splitlines(), 
        targets=["pyproject.toml"], 
        file_dep=["requirements.txt"],
        uptodate=[False]
        )

https://mozillascience.github.io/working-open-workshop/contributing/
https://gist.github.com/bollwyvl/f6aac8d4e68e5594fad2ae7a3cacc74b
https://gist.github.com/tonyfast/f74eb42f2a998d8e428a752ceb0cb1d1

should we pre install a bunch of different pytest opinions?