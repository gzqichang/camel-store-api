import os
from setuptools import setup, find_packages

setup(
    name='qapi',
    version='0.2.0',
    packages=['qapi'],
    exclude_package_data={'': ['*.pyc']},
    include_package_data=True,
    install_requires=[
        'django',
        'djangorestframework',
        'django-filter',
    ],
)
