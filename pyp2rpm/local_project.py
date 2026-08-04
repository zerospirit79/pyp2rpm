# -*- coding: utf-8 -*-
"""Helpers for reading project metadata from an unpacked local directory."""

from __future__ import absolute_import

import ast
import configparser
import logging
import os
import re
import sys

logger = logging.getLogger(__name__)

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def _read_text(path):
    with open(path, 'rb') as handle:
        data = handle.read()
    for encoding in ('utf-8', 'latin-1'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', 'replace')


def _strip_req(req):
    """Keep requirement string usable by pkg_resources.Requirement.parse."""
    if not req or not isinstance(req, str):
        return None
    req = req.strip()
    if not req or req == 'python':
        return None
    return req


def _collect_script_names(mapping):
    names = []
    if isinstance(mapping, dict):
        for name in mapping.keys():
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def _extract_console_scripts(entry_points):
    scripts = []
    if not entry_points:
        return scripts
    console = None
    if isinstance(entry_points, dict):
        console = entry_points.get('console_scripts')
    if isinstance(console, dict):
        scripts.extend(_collect_script_names(console))
    elif isinstance(console, (list, tuple)):
        for item in console:
            if not isinstance(item, str):
                continue
            equal_sign = item.find('=')
            name = item if equal_sign == -1 else item[:equal_sign]
            name = name.strip()
            if name:
                scripts.append(name)
    return scripts


def _load_toml(path):
    if tomllib is None:
        logger.warning(
            'Neither tomllib nor tomli is available; skipping {0}'.format(path))
        return {}
    with open(path, 'rb') as handle:
        return tomllib.load(handle)


def parse_pyproject(project_dir):
    """Return metadata dict extracted from pyproject.toml if present."""
    path = os.path.join(project_dir, 'pyproject.toml')
    if not os.path.isfile(path):
        return {}

    data = _load_toml(path)
    result = {
        'install_requires': [],
        'setup_requires': [],
        'tests_require': [],
        'extras_require': {},
        'scripts': [],
        'entry_points': {},
    }

    build_system = data.get('build-system') or {}
    for req in build_system.get('requires') or []:
        cleaned = _strip_req(req)
        if cleaned:
            result['setup_requires'].append(cleaned)

    project = data.get('project') or {}
    if project.get('name'):
        result['name'] = project['name']
    if project.get('version'):
        result['version'] = str(project['version'])
    if project.get('description'):
        result['description'] = project['description']
    if project.get('license'):
        license_val = project['license']
        if isinstance(license_val, dict):
            result['license'] = license_val.get('text') or license_val.get('file') or ''
        else:
            result['license'] = str(license_val)
    urls = project.get('urls') or {}
    if isinstance(urls, dict):
        result['project_urls'] = urls
        result['url'] = (urls.get('Homepage') or urls.get('homepage') or
                         urls.get('Source') or urls.get('Repository') or '')
    for req in project.get('dependencies') or []:
        cleaned = _strip_req(req)
        if cleaned:
            result['install_requires'].append(cleaned)

    optional = project.get('optional-dependencies') or {}
    if isinstance(optional, dict):
        extras = {}
        for extra, reqs in optional.items():
            extras[extra] = []
            for req in reqs or []:
                cleaned = _strip_req(req)
                if cleaned:
                    extras[extra].append(cleaned)
            if extra in ('test', 'tests', 'testing', 'check', 'dev'):
                result['tests_require'].extend(extras[extra])
        result['extras_require'] = extras

    scripts = []
    scripts.extend(_collect_script_names(project.get('scripts') or {}))
    project_entry_points = project.get('entry-points') or {}
    result['entry_points'] = project_entry_points if isinstance(
        project_entry_points, dict) else {}
    scripts.extend(_extract_console_scripts(result['entry_points']))

    # Poetry fallback
    poetry = (data.get('tool') or {}).get('poetry') or {}
    if poetry:
        if not result.get('name') and poetry.get('name'):
            result['name'] = poetry['name']
        if not result.get('version') and poetry.get('version'):
            result['version'] = str(poetry['version'])
        if not result.get('description') and poetry.get('description'):
            result['description'] = poetry['description']
        deps = poetry.get('dependencies') or {}
        if isinstance(deps, dict):
            for name, spec in deps.items():
                if name.lower() == 'python':
                    continue
                if isinstance(spec, dict):
                    version = spec.get('version', '')
                else:
                    version = spec if isinstance(spec, str) else ''
                version = (version or '').strip()
                if version.startswith('^') or version.startswith('~'):
                    version = version[1:]
                    req = '{0}>={1}'.format(name, version) if version else name
                elif version in ('*', '', 'latest'):
                    req = name
                else:
                    req = '{0}{1}'.format(name, version) if version and version[0] in '<>!=' else (
                        '{0}>={1}'.format(name, version) if version else name)
                cleaned = _strip_req(req)
                if cleaned:
                    result['install_requires'].append(cleaned)
        scripts.extend(_collect_script_names(poetry.get('scripts') or {}))

    result['scripts'] = sorted(set(scripts))

    return result


def parse_setup_cfg(project_dir):
    """Return metadata dict extracted from setup.cfg if present."""
    path = os.path.join(project_dir, 'setup.cfg')
    if not os.path.isfile(path):
        return {}

    parser = configparser.ConfigParser()
    try:
        parser.read(path)
    except configparser.Error as exc:
        logger.warning('Failed to parse {0}: {1}'.format(path, exc))
        return {}

    result = {
        'install_requires': [],
        'setup_requires': [],
        'tests_require': [],
        'extras_require': {},
        'scripts': [],
        'entry_points': {},
    }

    if parser.has_section('metadata'):
        meta = dict(parser.items('metadata'))
        if meta.get('name'):
            result['name'] = meta['name']
        if meta.get('version'):
            result['version'] = meta['version']
        if meta.get('description'):
            result['description'] = meta['description']
        if meta.get('license'):
            result['license'] = meta['license']
        if meta.get('url') or meta.get('home-page'):
            result['url'] = meta.get('url') or meta.get('home-page')

    def _split_reqs(value):
        reqs = []
        for line in (value or '').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            cleaned = _strip_req(line)
            if cleaned:
                reqs.append(cleaned)
        return reqs

    if parser.has_section('options'):
        options = dict(parser.items('options'))
        result['install_requires'] = _split_reqs(options.get('install_requires', ''))
        result['setup_requires'] = _split_reqs(options.get('setup_requires', ''))
        result['tests_require'] = _split_reqs(options.get('tests_require', ''))

    extras = {}
    if parser.has_section('options.extras_require'):
        for extra, value in parser.items('options.extras_require'):
            extras[extra] = _split_reqs(value)
            if extra in ('test', 'tests', 'testing', 'check', 'dev'):
                result['tests_require'].extend(extras[extra])
    result['extras_require'] = extras

    if parser.has_section('options.entry_points'):
        entry_points = {}
        for key, value in parser.items('options.entry_points'):
            lines = []
            for line in (value or '').splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    lines.append(line)
            entry_points[key] = lines
        result['entry_points'] = entry_points
        result['scripts'] = sorted(set(_extract_console_scripts(entry_points)))

    return result


def _literal_or_none(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def parse_setup_py(project_dir):
    """Best-effort static parse of setup.py for name/version/requires."""
    path = os.path.join(project_dir, 'setup.py')
    if not os.path.isfile(path):
        return {}

    source = _read_text(path)
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        logger.warning('Failed to parse {0}: {1}'.format(path, exc))
        return {}

    result = {
        'install_requires': [],
        'setup_requires': [],
        'tests_require': [],
        'extras_require': {},
        'scripts': [],
        'entry_points': {},
    }

    # Collect simple module-level assignments: name = <literal>
    assigns = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                value = _literal_or_none(node.value)
                if value is not None:
                    assigns[target.id] = value

    def resolve(node):
        literal = _literal_or_none(node)
        if literal is not None:
            return literal
        if isinstance(node, ast.Name) and node.id in assigns:
            return assigns[node.id]
        return None

    keywords = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != 'setup':
            continue
        for kw in node.keywords:
            if kw.arg:
                keywords[kw.arg] = resolve(kw.value)

    for key in ('name', 'version', 'description', 'license', 'url'):
        value = keywords.get(key)
        if isinstance(value, str) and value:
            result[key] = value

    for key in ('install_requires', 'setup_requires', 'tests_require'):
        value = keywords.get(key)
        if isinstance(value, (list, tuple)):
            result[key] = [r for r in (_strip_req(x) for x in value) if r]

    extras = keywords.get('extras_require')
    if isinstance(extras, dict):
        parsed = {}
        for extra, reqs in extras.items():
            if isinstance(reqs, (list, tuple)):
                parsed[extra] = [r for r in (_strip_req(x) for x in reqs) if r]
                if extra in ('test', 'tests', 'testing', 'check', 'dev'):
                    result['tests_require'].extend(parsed[extra])
        result['extras_require'] = parsed

    scripts = keywords.get('scripts')
    if isinstance(scripts, (list, tuple)):
        result['scripts'] = [os.path.basename(str(s))
                             for s in scripts if isinstance(s, str) and s]

    entry_points = keywords.get('entry_points')
    if isinstance(entry_points, dict):
        result['entry_points'] = entry_points
        result['scripts'] = sorted(set(
            result['scripts'] + _extract_console_scripts(entry_points)))

    # Fallback regex for simple assignments if AST literals failed
    if not result.get('name'):
        match = re.search(
            r'''name\s*=\s*['"]([^'"]+)['"]''', source)
        if match:
            result['name'] = match.group(1)
    if not result.get('version'):
        match = re.search(
            r'''version\s*=\s*['"]([^'"]+)['"]''', source)
        if match:
            result['version'] = match.group(1)

    result['scripts'] = sorted(set(result.get('scripts') or []))
    return result


def merge_metadata(*parts):
    """Merge metadata dicts; earlier parts win for scalars, lists are extended."""
    merged = {
        'install_requires': [],
        'setup_requires': [],
        'tests_require': [],
        'extras_require': {},
        'packages': set(),
        'py_modules': [],
        'scripts': [],
        'entry_points': {},
        'project_urls': {},
        'classifiers': [],
        'test_suite': None,
        'description': '',
        'long_description': '',
        'license': '',
        'url': '',
    }
    for part in parts:
        if not part:
            continue
        for key, value in part.items():
            if key in ('install_requires', 'setup_requires', 'tests_require'):
                for item in value or []:
                    if item not in merged[key]:
                        merged[key].append(item)
            elif key == 'extras_require' and isinstance(value, dict):
                merged['extras_require'].update(value)
            elif key == 'project_urls' and isinstance(value, dict):
                merged['project_urls'].update(value)
            elif key in merged and not merged.get(key) and value:
                merged[key] = value
            elif key not in merged and value:
                merged[key] = value
    return merged


def read_project_metadata(project_dir):
    """Aggregate metadata from pyproject.toml, setup.cfg and setup.py."""
    project_dir = os.path.abspath(project_dir)
    meta = merge_metadata(
        parse_pyproject(project_dir),
        parse_setup_cfg(project_dir),
        parse_setup_py(project_dir),
    )
    if not meta.get('name'):
        meta['name'] = os.path.basename(project_dir.rstrip(os.sep)) or 'package'
    if not meta.get('version'):
        meta['version'] = '0'
    if not meta.get('long_description') and meta.get('description'):
        meta['long_description'] = meta['description']
    return meta
