# deathbeds generalized automation framework

the deathbeds generalized automation framework provides opinionated tools for expanding content into development and documentation tools. `dgaf` sources opinions across the python/jupyter ecosystem so folks can focus on content without contest and context.

## what does `dgaf` do?

`dgaf` is a designed to be a compact CLI that will expands content into different environments for development, testing, and documentation. 

1. infer and export the environment from existing content.
2. install the dependencies
3. install the development package
4. build the package as a wheel
5. build a blog and documentation


## everything is documentation

### expanding environments




# development

    def task_dev():

install the requirements and use `dgaf` to generate and install dependencies.

        return dict(
            actions="""
    pip install -rrequirements.txt
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