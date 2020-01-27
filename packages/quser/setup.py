from setuptools import setup

setup(
    name='quser',
    version='0.1.0',
    packages=['quser'],
    exclude_package_data={'': ['*.pyc']},
    include_package_data=True,
    install_requires=[
        'django>=2.0',
        'djangorestframework>=3.8.2',
        'django-filter>=1.1.0',
        'django-simple-captcha==0.5.6',
        'markdown', 
    ],
)
