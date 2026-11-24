import pytest

from snapshot_fixtures import _add_submodule, _build_target


@pytest.fixture(scope="module")
def template_target(tmp_path_factory):
    """A plain target repo, built once per test module; copy it with `_copy_target`."""
    target, _ = _build_target(tmp_path_factory.mktemp("template"))
    return target


@pytest.fixture(scope="module")
def template_target_with_submodule(tmp_path_factory):
    """A target repo with a submodule at `sub`, built once per test module."""
    tmp_path = tmp_path_factory.mktemp("template-sub")
    target, env = _build_target(tmp_path)
    _add_submodule(tmp_path, target, env)
    return target
