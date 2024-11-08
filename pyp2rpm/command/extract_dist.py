import sys
import json
from setuptools import setup, find_packages  # Импорт setuptools


class extract_dist:  # Удален наследование от Command
    """Custom function to extract metadata."""
    class_metadata = None

    def __init__(self, metadata_from_setup):
        """Metadata dictionary is created."""
        self.metadata = {}
        self.fill_metadata(metadata_from_setup)

    def fill_metadata(self, metadata):
      self.metadata = {}
      for attr in ['setup_requires', 'tests_require', 'install_requires',
                   'packages', 'py_modules', 'scripts']:
          self.metadata[attr] = to_list(metadata.get(attr, []))

      try:
          for k, v in metadata.get('extras_require', {}).items():
              if k in ['test, docs', 'doc', 'dev']:
                  attr = 'setup_requires'
              else:
                  attr = 'install_requires'
              self.metadata[attr] += to_list(v)
      except (AttributeError, ValueError):
          pass # extras_require are skipped in case of wrong data format

      for attr in ['url', 'long_description', 'description', 'license']:
          self.metadata[attr] = to_str(metadata.get(attr))

      self.metadata['classifiers'] = to_list(metadata.get('classifiers', []))

      self.metadata['entry_points'] = metadata.get('entry_points')

      self.metadata['test_suite'] = metadata.get("test_suite") is not None


    def run(self):
        """Sends extracted metadata in json format to stdout."""
        if self.stdout:
            sys.stdout.write("extracted json data:\n" + json.dumps(
                self.metadata, default=to_str) + "\n")
        else:
            extract_dist.class_metadata = self.metadata

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
