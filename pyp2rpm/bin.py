import getpass
import locale
import logging
import os

from pyp2rpm.convertor import Convertor
from pyp2rpm import settings
from pyp2rpm import utils
from pyp2rpm.logger import (register_file_log_handler,
                            register_console_log_handler)

import click
try:
    from spec2scl.convertor import Convertor as SclConvertor
except ImportError:
    SclConvertor = None
except Exception as err:
    SclConvertor = None
    click.echo('Warning: An unexpected error occured when trying'
               ' to import spec2scl: {}'.format(err))


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


class Pyp2rpmCommand(click.Command):
    """Base class for pyp2rpm command.

    Modify the help message for SCL related options,
    to single them out in a separate group.
    """

    def format_options(self, ctx, formatter):
        """Writes SCL related options into the formatter as a separate
        group.
        """
        super(Pyp2rpmCommand, self).format_options(ctx, formatter)
        scl_opts = []
        for param in self.get_params(ctx):
            if isinstance(param, SclizeOption):
                scl_opts.append(param.get_scl_help_record(ctx))

        if scl_opts:
            with formatter.section('SCL related options'):
                formatter.write_dl(scl_opts)


class SclizeOption(click.Option):
    """Base class for SCL related options.

    Provide proper validation and help message formatting.
    """

    def handle_parse_result(self, ctx, opts, args):
        """Validate SCL related options before parsing."""
        if 'sclize' in opts and not SclConvertor:
            raise click.UsageError("Please install spec2scl package to "
                                   "perform SCL-style conversion")
        if self.name in opts and 'sclize' not in opts:
            raise click.UsageError(
                "`--{}` can only be used with --sclize option".format(
                    self.name))

        return super(SclizeOption, self).handle_parse_result(ctx, opts, args)

    def get_help_record(self, ctx):
        """Remove help record, so that it does not appear in Options
        section.
        """
        pass

    def get_scl_help_record(self, ctx):
        """Move help record, so that it appears in SCL options section."""
        return super(SclizeOption, self).get_help_record(ctx)


@click.command(context_settings=CONTEXT_SETTINGS, cls=Pyp2rpmCommand)
@click.option('-t',
              help='Template file (jinja2 format) to render (default: "{0}").'
              'Search order is 1) filesystem, 2) default templates.'.format(
                  settings.DEFAULT_TEMPLATE),
              metavar='TEMPLATE')
@click.option('-o',
              help='Default distro whose conversion rules to use '
              '(default:"{0}"). Default templates have their rules associated '
              'and ignore this.'.format(settings.DEFAULT_DISTRO),
              type=click.Choice(settings.KNOWN_DISTROS),
              default=settings.DEFAULT_DISTRO)
@click.option('-b',
              help='Base Python version to package for (fedora '
              'default: "{0}").'.format(settings.DEFAULT_PYTHON_VERSION),
              default=None,
              metavar='BASE_PYTHON')
@click.option('-p',
              help='Additional Python versions to include in the specfile '
              '(e.g -p2 for python2 subpackage). Can be specified multiple '
              'times. Specify additional version or use -b explicitly to '
              'disable default.',
              default=[],
              multiple=True, metavar='PYTHON_VERSIONS')
@click.option('-s',
              help='Spec file ~/rpmbuild/SPECS/python-package_name.spec will '
              'be created (default: prints spec file to stdout).',
              is_flag=True)
@click.option('--srpm',
              help='When used pyp2rpm will produce srpm instead of printing '
              'specfile into stdout.',
              is_flag=True)
@click.option('--proxy',
              help='Specify proxy in the form proxy.server:port.',
              default=None,
              metavar='PROXY')
@click.option('-r',
              help='Name of rpm package (overrides calculated name).',
              default=None,
              metavar='RPM_NAME')
@click.option('-d',
              help='Specify where to save package file, specfile and '
              'generated SRPM (default: "{0}").'.format(
                  settings.DEFAULT_PKG_SAVE_PATH),
              default=settings.DEFAULT_PKG_SAVE_PATH,
              metavar='SAVE_PATH')
@click.option('-v',
              help='Version of the package to download (ignored for '
              'local files).',
              metavar='VERSION')
@click.option('--prerelease',
              help='Use the latest release, even if it is a pre-release '
              '(default: disabled).',
              is_flag=True)
@click.option('--venv / --no-venv',
              help='Enable / disable metadata extraction from virtualenv '
              '(default: enabled).',
              default=True)
@click.option('--autonc/ --no-autonc',
              help='Enable / disable using automatic provides with '
              'a standardized name in dependencies declaration ('
              'default: disabled).',
              default=None)
@click.option('--sclize',
              help='Convert tags and macro definitions to SCL-style using '
              '`spec2scl` module. NOTE: SCL related options can be provided '
              'alongside this option.',
              is_flag=True)
# SCL related options
@click.option('--no-meta-runtime-dep',
              cls=SclizeOption,
              help='Don\'t add the runtime dependency on the scl '
              'runtime package.',
              is_flag=True)
@click.option('--no-meta-buildtime-dep',
              cls=SclizeOption,
              help='Don\'t add the buildtime dependency on the scl '
              'runtime package.',
              is_flag=True)
@click.option('--skip-functions',
              cls=SclizeOption,
              help='Comma separated list of transformer functions to skip.',
              default='',
              metavar='FUNCTIONS')
@click.option('--no-deps-convert',
              cls=SclizeOption,
              help='Don\'t convert dependency tags (mutually exclusive '
              'with --list-file).',
              is_flag=True)
@click.option('--list-file',
              cls=SclizeOption,
              help='List of the packages/provides, that will be in the SCL '
              '(to convert Requires/BuildRequires properly). Lines in '
              'the file are in form of "pkg-name %%{?custom_prefix}", where '
              'the prefix part is optional.',
              default=None,
              metavar='FILE_NAME')
@click.option('-l', '--local-dir',
              help='Path to a local project directory containing setup.py, '
              'setup.cfg or pyproject.toml. Metadata and dependencies are '
              'read from these files without building an sdist (alternative '
              'to PACKAGE; a directory can also be passed as PACKAGE). For '
              'altlinux template, BuildRequires are checked against Sisyphus '
              'via RDB API; packages absent in Sisyphus are listed after '
              'conversion.',
              type=click.Path(exists=True, file_okay=False, dir_okay=True,
                              resolve_path=True),
              default=None,
              metavar='DIRECTORY')
@click.option('--spec',
              help='Path to an existing SPEC file to update in place. '
              'Discovered BuildRequires/Requires (present in Sisyphus for '
              'altlinux) are inserted into this file instead of rendering a '
              'new SPEC from a template.',
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True),
              default=None,
              metavar='SPEC_FILE')
@click.argument('package', required=False, default=None)
def main(package, local_dir, spec, v, prerelease, d, s, r, proxy, srpm, p, b, o,
         t, venv, autonc, sclize, **scl_kwargs):
    """Convert PyPI package to RPM specfile or SRPM.

    \b
    \b\bArguments:
    PACKAGE             Provide PyPI name of the package, path to compressed
                        source file, or path to a local project directory.
                        Use -l/--local-dir as an alternative for directories.
                        Local directories are not built; dependencies are taken
                        from pyproject.toml / setup.cfg / setup.py.
                        Use --spec to update an existing SPEC file in place.
    """
    register_file_log_handler('/tmp/pyp2rpm-{0}.log'.format(getpass.getuser()))

    if srpm or s:
        register_console_log_handler()

    if local_dir and package:
        raise click.UsageError(
            'Provide either PACKAGE or --local-dir, not both.')
    if local_dir:
        package = local_dir
    if not package:
        raise click.UsageError(
            'Provide PACKAGE (PyPI name, archive path, or project directory) '
            'or --local-dir DIRECTORY.')
    if spec and (srpm or s):
        raise click.UsageError(
            '--spec cannot be combined with -s/--srpm; it updates the given '
            'SPEC file in place.')

    distro = o
    template = t or settings.DEFAULT_TEMPLATE
    template_base = os.path.splitext(template)[0]
    if template_base in settings.KNOWN_DISTROS:
        distro = template_base
    if not distro and not (b or p):
        raise click.UsageError("Default python versions for template {0} are "
                               "missing in settings, add them or use flags "
                               "-b/-p to set python versions.".format(t))

    logger = logging.getLogger(__name__)

    logger.info('Pyp2rpm initialized.')

    convertor = Convertor(package=package,
                          version=v,
                          prerelease=prerelease,
                          save_dir=d,
                          template=template,
                          distro=distro,
                          base_python_version=b,
                          python_versions=p,
                          rpm_name=r,
                          proxy=proxy,
                          venv=venv,
                          autonc=autonc)

    logger.debug(
        'Convertor: {0} created. Trying to convert.'.format(convertor))

    if spec:
        from pyp2rpm.spec_updater import update_spec_file
        data = convertor.extract_package_data()
        added = update_spec_file(
            spec,
            build_deps=getattr(data, 'build_deps', []),
            runtime_deps=getattr(data, 'runtime_deps', []))
        if added:
            click.echo('Updated {0}:'.format(spec), err=True)
            for line in added:
                click.echo('  + {0}'.format(line), err=True)
        else:
            click.echo(
                'No new dependencies to add to {0}.'.format(spec), err=True)
    else:
        converted = convertor.convert()
        logger.debug('Convertor: {0} succesfully converted.'.format(convertor))

        if sclize:
            converted = convert_to_scl(converted, scl_kwargs)

        if srpm or s:
            if r:
                spec_name = r + '.spec'
            else:
                prefix = 'python-' if not convertor.name.startswith(
                    'python-') else ''
                spec_name = prefix + convertor.name + '.spec'
            logger.info('Using name: {0} for specfile.'.format(spec_name))
            if d == settings.DEFAULT_PKG_SAVE_PATH:
                # default save_path is rpmbuild tree so we want to save spec
                # in  rpmbuild/SPECS/
                spec_path = d + '/SPECS/' + spec_name
            else:
                # if user provide save_path then save spec in provided path
                spec_path = d + '/' + spec_name
            spec_dir = os.path.dirname(spec_path)
            if not os.path.exists(spec_dir):
                os.makedirs(spec_dir)
            logger.debug('Opening specfile: {0}.'.format(spec_path))

            if not utils.PY3:
                converted = converted.encode('utf-8')
            with open(spec_path, 'w') as f:
                f.write(converted)
                logger.info('Specfile saved at: {0}.'.format(spec_path))

            if srpm:
                msg = utils.build_srpm(spec_path, d)
                if isinstance(msg, bytes):
                    for line in msg.decode(locale.getpreferredencoding(),
                                           errors='replace').split('\n'):
                        logger.info('rpmbuild -bs: {}'.format(line))
                else:
                    # As in python 3.4 and 3.5:
                    for line in msg.split('\n'):
                        logger.info('rpmbuild -bs: {}'.format(line))

        else:
            logger.debug('Printing specfile to stdout.')
            if utils.PY3:
                print(converted)
            else:
                print(converted.encode('utf-8'))
            logger.debug('Specfile printed.')

    if getattr(convertor, 'missing_deps', None):
        click.echo(
            '\nDependencies not found in Sisyphus:', err=True)
        for dep in convertor.missing_deps:
            click.echo('  - {0}'.format(dep), err=True)

    logger.info("That's all folks!")


def convert_to_scl(spec, scl_options):
    """Convert spec into SCL-style spec file using `spec2scl`.

    Args:
        spec: (str) a spec file
        scl_options: (dict) SCL options provided
    Returns:
        A converted spec file
    """
    scl_options['skip_functions'] = scl_options['skip_functions'].split(',')
    scl_options['meta_spec'] = None
    convertor = SclConvertor(options=scl_options)
    return str(convertor.convert(spec))
