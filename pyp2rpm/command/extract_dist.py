import sys
import json
from setuptools import Command
from setuptools.dist import Distribution

class extract_dist(Command):
    """Custom setuptools command to extract metadata from setup function."""
    description = "Extract metadata from setup function."
    user_options = [('stdout', None, 'print metadata in JSON format to stdout')]
    class_metadata = None

    def initialize_options(self):
        self.stdout = False

    def finalize_options(self):
        pass

    def run(self):
        metadata = self.extract_metadata()
        if self.stdout:
            print("extracted JSON data:\n", json.dumps(metadata, indent=2, default=str))
        else:
            extract_dist.class_metadata = metadata

    def extract_metadata(self):
        #  Получаем данные из self.distribution.  Этот метод работает, только если вызывается из контекста setuptools.setup()
        metadata = {}
        distribution = self.distribution  # Доступ к объекту Distribution

        # Обработка основных зависимостей
        for attr in ['setup_requires', 'tests_require', 'install_requires',
                     'packages', 'py_modules', 'scripts', 'package_data']:
            value = getattr(distribution, attr, [])
            metadata[attr] = self._normalize_value(value)

        # Обработка дополнительных зависимостей (extras_require)
        extras_require = getattr(distribution, 'extras_require', {})
        for key, value in extras_require.items():
            metadata.setdefault('extras_require', {}).update({key: self._normalize_value(value)})

        # Обработка метаданных
        for attr in ['url', 'long_description', 'description', 'license', 'classifiers']:
            value = getattr(distribution.metadata, attr, None)
            metadata[attr] = self._normalize_value(value)

        # Обработка entry_points
        entry_points = getattr(distribution, "entry_points", None)
        metadata['entry_points'] = entry_points if isinstance(entry_points, dict) else None

        # Обработка test_suite (булевое значение)
        metadata['test_suite'] = getattr(distribution, "test_suite", None) is not None

        return metadata

    def _normalize_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (list, tuple)):
            return [item.strip() for item in value]
        return value
