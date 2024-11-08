import sys
import json
from setuptools import Command  # Импорт Command из setuptools


class extract_dist(Command):
    """Custom distutils command to extract metadata form setup function."""
    description = ("Assigns self.distribution to class attribute to make "
                   "it accessible from outside a class.")
    user_options = [('stdout', None,
                     'print metadata in json format to stdout')]
    class_metadata = None
    stdout = False

    def initialize_options(self):
        """Sets default value of the stdout option."""
        self.stdout = False

    def finalize_options(self):
        pass  # Abstract method from Command needs to be overridden

    def run(self):
        """Sends extracted metadata in json format to stdout if stdout
        option is specified, assigns metadata dictionary to class_metadata
        variable otherwise.
        """
        metadata = self.get_metadata()
        if self.stdout:
            sys.stdout.write("extracted json data:\n" + json.dumps(
                metadata, default=to_str) + "\n")
        else:
            extract_dist.class_metadata = metadata

    def get_metadata(self):
        metadata = {}

        for attr in ['setup_requires', 'tests_require', 'install_requires',
                     'packages', 'py_modules', 'scripts']:
            metadata[attr] = to_list(getattr(self.distribution, attr, []))

        try:
            for k, v in getattr(self.distribution, 'extras_require', {}).items():
                if k in ['test, docs', 'doc', 'dev']:
                    attr = 'setup_requires'
                else:
                    attr = 'install_requires'
                metadata[attr] += to_list(v)
        except (AttributeError, ValueError):
            pass  # extras_require are skipped in case of wrong data format

        for attr in ['url', 'long_description', 'description', 'license']:
            metadata[attr] = to_str(
                getattr(self.distribution.metadata, attr, None))

        metadata['classifiers'] = to_list(
            getattr(self.distribution.metadata, 'classifiers', []))

        if isinstance(getattr(self.distribution, "entry_points", None), dict):
            metadata['entry_points'] = self.distribution.entry_points
        else:
            metadata['entry_points'] = None

        metadata['test_suite'] = getattr(
            self.distribution, "test_suite", None) is not None
        return metadata

def to_list(var):
    """Checks if given value is a list, tries to convert, if it is not."""
    if var is None:
        return []
    if isinstance(var, str):
        var = var.split('\n')
    elif not isinstance(var, list):
        try:
            var = list(var)
        except TypeError:
            raise ValueError("{} cannot be converted to the list.".format(var))
    return var


def to_str(var):
    """Similar to to_list function, but for string attributes."""
    try:
        return str(var)
    except TypeError:
        raise ValueError("{} cannot be converted to string.".format(var))

# Example of how to use the class
# metadata_dict = {"name": "mypackage", "version": "0.1.0", "packages": ["mypackage"], "install_requires": ["requests"]}
# extractor = extract_dist(metadata_dict)
# extractor.run()
