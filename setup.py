# -*- coding: utf-8 -*-
from setuptools import setup

packages = ['fancy_dataclass']

package_data = {'': ['*']}

setup_kwargs = {
    'name': 'fancy-dataclass',
    'version': '0.1.0',
    'description': 'Classes for augmenting dataclasses with additional functionality.',
    'long_description': None,
    'author': 'Jeremy Silver',
    'author_email': 'jeremys@nessiness.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=3.8,<4.0',
}


setup(**setup_kwargs)

