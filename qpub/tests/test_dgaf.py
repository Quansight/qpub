import doit
import qpub


def test_file():
    qpub.File("qpub/tests/test_qpub.py")
    deps = qpub.File("qpub/tests/test_qpub.py").imports()
    assert deps == {"qpub", "doit"}


def test_load_dump(tmpdir):
    file = qpub.File(tmpdir / "test.toml")
    assert not file.load()
    data = dict(foo=[1, 2])
    file.dump(data)
    assert file.load() == data
    file.unlink()
    assert not file


def test_merge():
    assert qpub.merge(dict(b=dict(a=[1])), dict(b=dict(a=[2]))) == dict(
        b=dict(a=[1, 2])
    )
