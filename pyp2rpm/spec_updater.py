# -*- coding: utf-8 -*-
"""Update an existing RPM SPEC with discovered Python dependencies."""

from __future__ import absolute_import

import logging
import re

logger = logging.getLogger(__name__)

_DEP_LINE_RE = re.compile(
    r'^(?P<tag>BuildRequires(?:\([^)]*\))?|Requires(?:\([^)]*\))?)\s*:\s*'
    r'(?P<body>.+?)\s*$'
)

_VERSION_SPLIT_RE = re.compile(
    r'\s+(?:>=|<=|==|!=|<>|=|>|<|~=)'
)

# Lines after which preamble dependency block ends.
_PREAMBLE_END_RE = re.compile(
    r'^%(description|package|prep|build|install|check|files|changelog)\b'
)

# Do not auto-insert these even if present in extracted deps.
_SKIP_INSERT = frozenset({
    'python2-devel',
    'python3-devel',
    'python-devel',
    'rpm-build-pyproject',
    'setuptools',
    'python3(setuptools)',
    'wheel',
    'python3(wheel)',
})


def capability_name(body):
    """Extract capability/package token from a Requires body."""
    body = body.strip()
    if not body:
        return ''
    if body.startswith('('):
        return body
    return _VERSION_SPLIT_RE.split(body, 1)[0].strip()


def format_dep_line(tag, dep):
    """Format one SPEC dependency line from pyp2rpm dep triple."""
    # dep: [tag_from_extractor, name, '{name}' or '{name} >= 1.0']
    name = dep[1]
    fmt = dep[2] if len(dep) > 2 else '{name}'
    try:
        body = fmt.format(name=name)
    except (KeyError, IndexError, ValueError):
        body = name
    return '{0}: {1}'.format(tag, body)


def _existing_capabilities(lines, tag_prefix=None):
    """Return set of capability names already declared in SPEC lines.

    If ``tag_prefix`` is given (e.g. ``'Requires'`` or ``'BuildRequires'``),
    only that tag family is considered.
    """
    found = set()
    for line in lines:
        match = _DEP_LINE_RE.match(line)
        if not match:
            continue
        tag = match.group('tag')
        if tag_prefix and not tag.startswith(tag_prefix):
            continue
        found.add(capability_name(match.group('body')))
    return found


def _preamble_end_index(lines):
    """Index of first section header that ends the SPEC preamble."""
    for idx, line in enumerate(lines):
        if _PREAMBLE_END_RE.match(line):
            return idx
    return len(lines)


def _last_tag_index(lines, end, tag_prefix):
    """Last index before ``end`` whose line starts with given tag prefix."""
    last = -1
    for idx in range(end):
        match = _DEP_LINE_RE.match(lines[idx])
        if not match:
            continue
        if match.group('tag').startswith(tag_prefix):
            last = idx
    return last


def deps_to_lines(deps, tag):
    """Convert extractor deps to SPEC lines for the given tag."""
    lines = []
    for dep in deps or []:
        if not dep or len(dep) < 2:
            continue
        name = dep[1]
        if name in _SKIP_INSERT:
            continue
        # Prefer explicit tag (BuildRequires / Requires).
        lines.append(format_dep_line(tag, dep))
    return lines


def update_spec_content(content, build_deps=None, runtime_deps=None):
    """Insert missing BuildRequires/Requires into SPEC text.

    Returns:
        (new_content, added_lines)
    """
    # Preserve newline style
    newline = '\r\n' if '\r\n' in content else '\n'
    # splitlines() drops final newline info; keep trailing newline flag
    had_trailing = content.endswith(('\n', '\r'))
    lines = content.splitlines()

    existing_br = _existing_capabilities(lines, 'BuildRequires')
    existing_req = _existing_capabilities(lines, 'Requires')
    end = _preamble_end_index(lines)

    to_add_br = []
    for line in deps_to_lines(build_deps, 'BuildRequires'):
        cap = capability_name(_DEP_LINE_RE.match(line).group('body'))
        if cap and cap not in existing_br:
            to_add_br.append(line)
            existing_br.add(cap)

    to_add_req = []
    for line in deps_to_lines(runtime_deps, 'Requires'):
        cap = capability_name(_DEP_LINE_RE.match(line).group('body'))
        if cap and cap not in existing_req:
            to_add_req.append(line)
            existing_req.add(cap)

    added = []
    if not to_add_br and not to_add_req:
        return content, added

    # Insert BuildRequires after last BuildRequires in preamble, else
    # before preamble end.
    if to_add_br:
        br_at = _last_tag_index(lines, end, 'BuildRequires')
        insert_at = br_at + 1 if br_at >= 0 else end
        lines[insert_at:insert_at] = to_add_br
        added.extend(to_add_br)
        end += len(to_add_br)

    if to_add_req:
        req_at = _last_tag_index(lines, end, 'Requires')
        if req_at >= 0:
            insert_at = req_at + 1
        else:
            # After BuildRequires block if any, else before preamble end.
            br_at = _last_tag_index(lines, end, 'BuildRequires')
            insert_at = br_at + 1 if br_at >= 0 else end
        lines[insert_at:insert_at] = to_add_req
        added.extend(to_add_req)

    new_content = newline.join(lines)
    if had_trailing:
        new_content += newline
    return new_content, added


def update_spec_file(spec_path, build_deps=None, runtime_deps=None):
    """Update SPEC file in place. Returns list of added lines."""
    with open(spec_path, 'r') as handle:
        content = handle.read()
    new_content, added = update_spec_content(
        content, build_deps=build_deps, runtime_deps=runtime_deps)
    if added:
        with open(spec_path, 'w') as handle:
            handle.write(new_content)
        logger.info('Updated SPEC {0}: added {1} line(s).'.format(
            spec_path, len(added)))
    else:
        logger.info('SPEC {0}: no new dependencies to add.'.format(spec_path))
    return added
