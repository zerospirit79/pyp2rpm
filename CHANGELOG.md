# Changelog

## 3.4.0

- Add `-l` / `--local-dir` to convert an unpacked local project without building an sdist.
- Read project metadata and dependencies from `pyproject.toml`, `setup.cfg` and `setup.py`.
- For the `altlinux` template, resolve `BuildRequires` / `Requires` against Sisyphus via the RDB API.
- Print dependencies that are absent in Sisyphus after conversion.
- Add `--spec` to update an existing SPEC file in place with discovered dependencies.
- Improve ALT Linux packaging template and `python3(...)` dependency naming.
- Add maintainer/author: Pavel Shilov \<zerospirit@altlinux.org\>.

## 3.3.10

- Fix tests on Python 3.12.
