import pytest

sample_script = """'a script for testing.'
__version__ = "0.1.0"
import pandas

def main():
    return pandas.DataFrame()
"""

test_script = """
import hypothesis

def test_main():
    import sample_project
    assert len(sample_project.main())
"""


@pytest.fixture
def simple_python_script_project(tmp_path):
    """a  """
    path = tmp_path / "sample_project.py"
    test = tmp_path / "test_project.py"
    path.write_text(sample_script)
    test.write_text(test_script)
    yield tmp_path
    path.unlink()
    test.unlink()


@pytest.fixture
def simple_python_directory_project(tmp_path):
    path = tmp_path / "sample_project.py"
    tests = tmp_path / "tests"
    test = tests / "test_project.py"
    path.write_text(sample_script)
    test.write_text(test_script)
    yield tmp_path
    path.unlink()


@pytest.fixture
def simple_python_src_project(tmp_path):
    src = tmp_path / "src"
    tests = src / "tests"
    test = tests / "test_project.py"
    path = src / "sample_project.py"
    path.write_text(sample_script)
    test.write_text(test_script)
    yield tmp_path
    src.unlink()