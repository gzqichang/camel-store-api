import os
from setuptools import setup, find_packages

setup(
    name='qsmstoken',
    version='0.1.0',
    packages=['qsmstoken'],
    exclude_package_data={'':['*.pyc']},
    include_package_data=True,
    install_requires=[
        'django',
	'aliyun-python-sdk-core',
	'aliyun-python-sdk-dysmsapi',
    ],
)
