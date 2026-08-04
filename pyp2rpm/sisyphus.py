"""Check whether Python dependencies exist as packages in ALT Sisyphus."""

from __future__ import absolute_import

import logging
import re
try:
    from urllib.request import urlopen, HTTPError
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import urlopen, HTTPError
    from urllib import urlencode

logger = logging.getLogger(__name__)

RDB_API = 'https://rdb.altlinux.org/api'
DEFAULT_BRANCH = 'sisyphus'

# Always kept in the SPEC regardless of repository lookup.
ALWAYS_KEEP = frozenset({
    'python2-devel',
    'python3-devel',
    'python-devel',
    'rpm-build-pyproject',
    'setuptools',
    'python3(setuptools)',
    'wheel',
    'python3(wheel)',
    'pytest',
    'python3(pytest)',
    'sphinx',
    'python3(sphinx)',
})

_PROVIDES_RE = re.compile(r'^python3\((.+)\)$')
_MODULE_RE = re.compile(r'^python3-module-(.+)$')


def provides_to_src_name(dep_name):
    """Map a dependency token to ALT source package name.

    Examples:
        python3(click) -> python3-module-click
        python3-module-click -> python3-module-click
        click -> python3-module-click
    """
    if not dep_name:
        return None
    name = dep_name.strip()
    match = _PROVIDES_RE.match(name)
    if match:
        return 'python3-module-{0}'.format(match.group(1))
    match = _MODULE_RE.match(name)
    if match:
        return name
    if name.startswith('python3dist(') or name.startswith('python2dist('):
        inner = name[name.find('(') + 1:-1]
        return 'python3-module-{0}'.format(inner)
    if name.startswith('python-') or name.startswith('python3-'):
        base = re.sub(r'^python3?-?', '', name)
        return 'python3-module-{0}'.format(base)
    return 'python3-module-{0}'.format(name)


def package_exists(src_name, branch=DEFAULT_BRANCH, opener=None):
    """Return True if source package exists in the given RDB branch."""
    if not src_name:
        return False
    query = urlencode({'branch': branch, 'name': src_name})
    url = '{0}/site/pkghash_by_name?{1}'.format(RDB_API, query)
    open_url = opener or urlopen
    try:
        response = open_url(url)
        try:
            body = response.read()
        finally:
            response.close()
        return bool(body)
    except HTTPError as exc:
        if getattr(exc, 'code', None) == 404:
            return False
        logger.warning('RDB HTTP error for {0}: {1}'.format(src_name, exc))
        return False
    except Exception as exc:
        logger.warning('RDB lookup failed for {0}: {1}'.format(src_name, exc))
        return False


def filter_deps(deps, branch=DEFAULT_BRANCH, opener=None):
    """Keep only dependencies present in Sisyphus (or always-kept names).

    Args:
        deps: list of [tag, name, version_fmt] lists as used by templates.
        branch: RDB repository branch.
        opener: optional urlopen-compatible callable (for tests).

    Returns:
        (kept_deps, missing_names) where missing_names are original dep names
        not found in Sisyphus.
    """
    kept = []
    missing = []
    cache = {}

    for dep in deps or []:
        if not dep or len(dep) < 2:
            continue
        name = dep[1]
        if name in ALWAYS_KEEP:
            kept.append(dep)
            continue

        src_name = provides_to_src_name(name)
        if src_name not in cache:
            cache[src_name] = package_exists(src_name, branch=branch,
                                             opener=opener)
        if cache[src_name]:
            kept.append(dep)
        else:
            missing.append(name)
            logger.info('Dependency not in {0}: {1} ({2})'.format(
                branch, name, src_name))

    # unique missing, stable order
    seen = set()
    unique_missing = []
    for name in missing:
        if name not in seen:
            seen.add(name)
            unique_missing.append(name)
    return kept, unique_missing
