import doit
import typer
import dgaf


def test_file():
    dgaf.File('dgaf/tests/test_dgaf.py')
    deps = dgaf.File('dgaf/tests/test_dgaf.py').imports()
    assert deps == {"dgaf", "doit"}


def test_load_dump(tmpdir):
    file = dgaf.File(tmpdir/'test.toml')
    assert not file.load()
    data = dict(foo=[1, 2])
    file.dump(data)
    assert file.load() == data
    file.unlink()
    assert not file


def test_merge():
    assert dgaf.merge(dict(b=dict(a=[1])), dict(
        b=dict(a=[2]))) == dict(b=dict(a=[1, 2]))


def test_dot_env(tmpdir):
    import os
    file = dgaf.File(tmpdir/'.env')
    assert file.load() == dict(os.environ)
    file.write_text("FOO=42")
    assert file.load()["FOO"] == "42"


def test_cli(cli_runner):
    import dgaf.__main__
    cli_runner.invoke(typer.main.get_command(
        dgaf.__main__.app), "--help".split())
