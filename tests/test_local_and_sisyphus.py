# -*- coding: utf-8 -*-
import os

import pytest

from pyp2rpm.local_project import (
    parse_pyproject, parse_setup_py, read_project_metadata)
from pyp2rpm.sisyphus import (
    filter_deps, package_exists, provides_to_src_name)


class FakeResponse(object):
    def __init__(self, body=b'{"pkghash": "1"}'):
        self.body = body

    def read(self):
        return self.body

    def close(self):
        pass


class FakeHTTPError(Exception):
    def __init__(self, code):
        self.code = code


def test_provides_to_src_name():
    assert provides_to_src_name('python3(click)') == 'python3-module-click'
    assert provides_to_src_name('python3-module-click') == 'python3-module-click'
    assert provides_to_src_name('click') == 'python3-module-click'


def test_filter_deps_keeps_found_and_reports_missing(monkeypatch):
    import pyp2rpm.sisyphus as sisyphus

    def fake_exists(src_name, branch='sisyphus', opener=None):
        return src_name == 'python3-module-click'

    monkeypatch.setattr(sisyphus, 'package_exists', fake_exists)
    deps = [
        ['BuildRequires', 'python3(click)', '{name}'],
        ['BuildRequires', 'python3(not-in-sisyphus)', '{name}'],
        ['BuildRequires', 'python3(setuptools)', '{name}'],
    ]
    kept, missing = filter_deps(deps)
    assert [d[1] for d in kept] == ['python3(click)', 'python3(setuptools)']
    assert missing == ['python3(not-in-sisyphus)']


def test_parse_setup_py_utest():
    tests_dir = os.path.split(os.path.abspath(__file__))[0]
    project = os.path.join(tests_dir, 'test_data', 'utest')
    meta = read_project_metadata(project)
    assert meta['name'] == 'utest'
    assert meta['version'] == '0.1.0'
    assert any('pyp2rpm' in r for r in meta['install_requires'])


def test_parse_pyproject_dependencies(tmp_path):
    pyproject = tmp_path / 'pyproject.toml'
    pyproject.write_text(
        '[project]\n'
        'name = "demo"\n'
        'version = "1.2.3"\n'
        'dependencies = ["requests>=2.0", "click"]\n'
        '\n'
        '[build-system]\n'
        'requires = ["setuptools", "wheel"]\n',
        encoding='utf-8')
    meta = parse_pyproject(str(tmp_path))
    assert meta['name'] == 'demo'
    assert meta['version'] == '1.2.3'
    assert 'click' in meta['install_requires']
    assert 'setuptools' in meta['setup_requires']


def test_parse_pyproject_collects_scripts(tmp_path):
    pyproject = tmp_path / 'pyproject.toml'
    pyproject.write_text(
        '[project]\n'
        'name = "displayctl"\n'
        'version = "0.1.0"\n'
        'dependencies = ["click"]\n'
        '\n'
        '[project.scripts]\n'
        'displayctl = "displayctl.cli:main"\n'
        '\n'
        '[project.entry-points.console_scripts]\n'
        'displayctl-helper = "displayctl.cli:helper"\n'
        '\n'
        '[tool.poetry]\n'
        'name = "displayctl"\n'
        '\n'
        '[tool.poetry.scripts]\n'
        'displayctl-poetry = "displayctl.cli:poetry_main"\n',
        encoding='utf-8')
    meta = parse_pyproject(str(tmp_path))
    assert 'displayctl' in meta['scripts']
    assert 'displayctl-helper' in meta['scripts']
    assert 'displayctl-poetry' in meta['scripts']
