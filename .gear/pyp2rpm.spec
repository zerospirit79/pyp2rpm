%define _unpackaged_files_terminate_build 1
%define mod_name %pypi_name
%define pypi_name pyp2rpm

%def_without check

Name: python3-module-%pypi_name

Version: 3.4.0
Release: alt1
Summary: Tool to convert a package from PyPI to RPM SPECFILE or to generate SRPM.  
License: MIT
Group: Development/Python3
Url: https://pypi.org/project/pyp2rpm/
Vcs: https://github.com/zerospirit79/pyp2rpm 
BuildArch: noarch

Source0: %name-%version.tar

BuildRequires(pre): rpm-build-pyproject
BuildRequires: rpmdevtools
BuildRequires: python3(setuptools)
BuildRequires: python3(wheel)
BuildRequires: python3(jinja2)
BuildRequires: python3(click)
BuildRequires: python3(flexmock)
BuildRequires: python3(virtualenv)
BuildRequires: python3-module-virtualenvapi
BuildRequires: python3-module-dnf

%if_with check
BuildRequires: python3(pytest)
BuildRequires: python3(iniconfig)
BuildRequires: python3(packaging)
BuildRequires: python3(attrs)
BuildRequires: python3(pluggy)
BuildRequires: python3(scripttest)
%endif

Requires: python3(virtualenv)
Requires: rpmdevtools
Requires: python3(setuptools)
Requires: python3(jinja2)
Requires: python3(click)
Requires: python3-module-virtualenvapi
Requires: python3-module-dnf

%py3_provides %pypi_name

%description
%summary

%prep
%setup

%build
%pyproject_build

%install
%pyproject_install
install -Dpm644 %pypi_name.1 -t %buildroot%_man1dir

%check
#export PYTHONPATH=%buildroot%python3_sitelibdir
#py.test-3 -vv -m "not webtest" -k "not TestMetadataExtractor"

%files
%doc README.md
%_bindir/%pypi_name
%python3_sitelibdir/%pypi_name/
%python3_sitelibdir/%pypi_name-%version.dist-info
%_man1dir/%pypi_name.1*


%changelog
* Tue Aug 04 2026 Pavel Shilov <zerospirit@altlinux.ru> 3.4.0-alt1
- support source archives with pyproject.toml/setup.cfg but without setup.py
- drop deprecated pkg_resources usage (name normalization and deps parsing)

* Fri Nov 08 2024 Pavel Shilov <zerospirit@altlinux.ru> 3.3.10-alt1
- initial build for Sisyphus
