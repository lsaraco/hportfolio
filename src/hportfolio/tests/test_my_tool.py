"""Test for my tool function."""

from my_project import my_tool


def test_my_tool():
    """Unit test for  my_tool function."""
    assert my_tool(arg=True)
    assert not my_tool(arg=False)
