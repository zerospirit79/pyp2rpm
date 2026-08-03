{{ data.credit_line }}
{% from "macros.spec" import underscored_or_pypi -%}
%define _unpackaged_files_terminate_build 1
%define pypi_name {{ data.name|lower }}
{%- if data.srcname %}
%define srcname {{ data.srcname }}
{%- endif %}

%def_with check

Name: python3-module-%pypi_name
Version: {{ data.version | rpm_version(False) }}
Release: alt1
Summary: {{ data.summary }}
License: {{ data.license }}
Group: Development/Python3
Url: {{ data.home_page }}

{%- if not data.has_extension %}
BuildArch: noarch
{%- endif %}

Source: %name-%version.tar

BuildRequires(pre): rpm-build-pyproject
BuildRequires: python3(setuptools)
BuildRequires: python3(wheel)
{%- for dep in data.build_deps %}
{%- if dep[1] not in ["python2-devel", "python3-devel", "python-devel", "rpm-build-pyproject", "setuptools", "python3(setuptools)", "wheel", "python3(wheel)"] %}
{{ dep[0] }}: {{ dep[2].format(name=dep[1]) }}
{%- endif %}
{%- endfor %}
{%- if data.sphinx_dir %}
BuildRequires: python3(sphinx)
{%- endif %}

%if_with check
BuildRequires: python3(pytest)
{%- for dep in data.runtime_deps %}
{%- if dep[1] not in ["setuptools", "python3(setuptools)"] %}
BuildRequires: {{ dep[2].format(name=dep[1]) }}
{%- endif %}
{%- endfor %}
%endif

{%- for dep in data.runtime_deps %}
{%- if dep[1] not in ["setuptools", "python3(setuptools)"] %}
{{ dep[0] }}: {{ dep[2].format(name=dep[1]) }}
{%- endif %}
{%- endfor %}

%py3_provides %pypi_name

%description
{{ data.description|truncate(400)|wordwrap }}
{%- if data.sphinx_dir %}

%package doc
Summary: Documentation for %pypi_name
Group: Development/Documentation
BuildArch: noarch

%description doc
Documentation for %pypi_name.
{%- endif %}

%prep
%setup -q -n {{ data.dirname|default("%{pypi_name}-%{version}", true) }}
{%- if data.has_bundled_egg_info %}
rm -rf %pypi_name.egg-info
{%- endif %}

%build
%pyproject_build
{%- if data.sphinx_dir %}
# generate html docs
PYTHONPATH=${PWD} sphinx-build-3 {{ data.sphinx_dir }} html
rm -rf html/.{doctrees,buildinfo}
{%- endif %}

%install
%pyproject_install

%check
%if_with check
{%- if data.has_test_suite %}
%pyproject_run_pytest -v
{%- else %}
:
{%- endif %}
%endif

%files
{%- if data.doc_files %}
%doc {{ data.doc_files|join(" ") }}
{%- endif %}
{%- if data.doc_license %}
%doc {{ data.doc_license|join(" ") }}
{%- endif %}
{%- for script in data.scripts %}
%_bindir/{{ script }}
{%- endfor %}
{%- if data.has_packages %}
{%- for package in data.packages %}
%python3_sitelibdir/{{ package | package_to_path(data.name) }}/
{%- endfor %}
{%- elif data.py_modules %}
{%- for module in data.py_modules %}
%python3_sitelibdir/{{ data.name | module_to_path(module) }}.py
%python3_sitelibdir/__pycache__/*
{%- endfor %}
{%- else %}
%python3_sitelibdir/{{ underscored_or_pypi(data.name, data.underscored_name) }}/
{%- endif %}
%python3_sitelibdir/%{pyproject_distinfo %pypi_name}/
{%- if data.sphinx_dir %}

%files doc
%doc html/
{%- endif %}

%changelog
* {{ data.changelog_date_packager }} {{ data.version | rpm_version(False) }}-alt1
- Initial build for Sisyphus.
