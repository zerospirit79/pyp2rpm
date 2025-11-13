{{ data.credit_line }}
{% from 'macros.spec' import dependencies, for_python_versions, underscored_or_pypi, macroed_url -%}
%global pypi_name {{ data.name }}
%define name {{ data.pkg_name | macroed_pkg_name(data.srcname) }}

Name:           %{name}
Version:        {{ data.version | rpm_version(False) }}
Release:        alt1
Summary:        {{ data.summary }}
License:        {{ data.license | join(' ') }}
URL:            {{ data.url }}
Source0:        %{name}-%{version}.tar.gz
{%- if not data.has_extension %}
BuildArch:      noarch
{%- endif %}
{%- for pv in data.sorted_python_versions %}
{{ dependencies(data.build_deps, False, pv, data.base_python_version, False) }}
{%- endfor %}
# BuildRequires:  Зависимости для сборки.  Обязательно укажите все необходимые пакеты!
# BuildRequires:  python3-devel, python3-setuptools, python3-wheel
BuildRequires:  {{ data.buildrequires | join(' ') }} # Добавьте сюда все ваши BuildRequires


%description
{{ data.description|truncate(400)|wordwrap }}
{% for pv in data.sorted_python_versions %}
%package -n     {{data.pkg_name|macroed_pkg_name(data.srcname)|name_for_python_version(pv, True) }}
Summary:        %{summary}
%{?python_provide:%python_provide {{data.pkg_name|macroed_pkg_name(data.srcname)|name_for_python_version(pv, True)}}}
{{ dependencies(data.runtime_deps, True, pv, pv) }}
%description -n {{data.pkg_name|macroed_pkg_name(data.srcname)|name_for_python_version(pv, True) }}
{{ data.description|truncate(400)|wordwrap }}
{% endfor -%}
{%- if data.sphinx_dir %}
%package -n {{ data.pkg_name|macroed_pkg_name(data.srcname)|name_for_python_version(None, True) }}-doc
Summary:        {{ data.name }} documentation
%description -n {{ data.pkg_name|macroed_pkg_name(data.srcname)|name_for_python_version(None, True) }}-doc
Documentation for {{ data.name }}
{%- endif %}

%prep
%setup -q

%build
{% for pv in data.sorted_python_versions %}
%pyproject_build:
 %{__python{{ pv }}} -m build --wheel --no-isolation
{% endfor %}

{% if data.sphinx_dir %}
 PYTHONPATH=${PWD} %{__python{{ data.base_python_version }}} {{ "sphinx-build"|script_name_for_python_version(data.base_python_version, False, True) }} {{ data.sphinx_dir }} html
 rm -rf html/.{doctrees,buildinfo}
{% endif %}


%install
{% for pv in data.sorted_python_versions + [data.base_python_version] %}
%pyproject_install:
 %{__python{{ pv }}} -m pip install --root=%{buildroot} .
{% endfor %}

# Удаление скриптов, если необходима переустановка (только для базовой версии Python)
{% if data.python_versions and data.scripts %}
 rm -rf %{buildroot}%{_bindir}/*
{% endif %}


%check
{% if data.has_test_suite %}
{% for pv in data.sorted_python_versions %}
 %{__python{{ pv }}} setup.py test
{% endfor %}
{% endif %}


%files
%defattr(-,root,root,-)
{% for pv in data.sorted_python_versions %}
%{{ name }}py{{ pv }}:
 {% for file_pattern in iles_for_python_version(self, pv) %}
 {{ file_pattern }}
 {% endfor %}
{% endfor %}

{% if data.sphinx_dir %}
%defattr(-,root,root,-)
%{{ name }}doc:
 html/
{% endif %}


%changelog
* {{ data.changelog_date_packager }} - {{ data.version | rpm_version(False) }}-%{release}
- Initial package.
