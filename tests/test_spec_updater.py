# -*- coding: utf-8 -*-
from pyp2rpm.spec_updater import (
    capability_name, update_spec_content, update_spec_file)


SAMPLE_SPEC = """\
Name: python3-module-demo
Version: 1.0
Release: alt1
Summary: Demo
License: MIT
Group: Development/Python3
Url: https://example.com
BuildArch: noarch

Source: %name-%version.tar

BuildRequires(pre): rpm-build-pyproject
BuildRequires: python3(setuptools)
BuildRequires: python3(wheel)

%description
Demo package.

%prep
%setup
"""


def test_capability_name():
    assert capability_name('python3(click) >= 8') == 'python3(click)'
    assert capability_name('python3(setuptools)') == 'python3(setuptools)'


def test_update_spec_adds_missing_deps():
    build = [
        ['BuildRequires', 'python3(setuptools)', '{name}'],
        ['BuildRequires', 'python3(click)', '{name} >= 8'],
    ]
    runtime = [
        ['Requires', 'python3(click)', '{name} >= 8'],
        ['Requires', 'python3(requests)', '{name}'],
    ]
    new, added = update_spec_content(SAMPLE_SPEC, build, runtime)
    assert 'BuildRequires: python3(click) >= 8' in new
    assert 'Requires: python3(click) >= 8' in new
    assert 'Requires: python3(requests)' in new
    # setuptools already present — not duplicated
    assert new.count('BuildRequires: python3(setuptools)') == 1
    # same capability may appear in both BuildRequires and Requires
    assert 'BuildRequires: python3(click) >= 8' in added
    assert 'Requires: python3(click) >= 8' in added
    assert '%description' in new
    # Requires inserted before %description
    assert new.index('Requires: python3(requests)') < new.index('%description')


def test_update_spec_noop_when_present():
    build = [['BuildRequires', 'python3(setuptools)', '{name}']]
    new, added = update_spec_content(SAMPLE_SPEC, build, [])
    assert added == []
    assert new == SAMPLE_SPEC


def test_update_spec_file(tmp_path):
    path = tmp_path / 'demo.spec'
    path.write_text(SAMPLE_SPEC, encoding='utf-8')
    added = update_spec_file(
        str(path),
        build_deps=[['BuildRequires', 'python3(click)', '{name}']],
        runtime_deps=[])
    text = path.read_text(encoding='utf-8')
    assert added == ['BuildRequires: python3(click)']
    assert 'BuildRequires: python3(click)' in text
