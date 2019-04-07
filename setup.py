#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['cryptography==2.4.2', 'netmiko']

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="David Paul Cruz",
    author_email='davidcruz72@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Palo Alto Networks Utilities",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='panw_utils',
    name='panw_utils',
    packages=find_packages(include=['panw_utils']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/dapacruz/panw-utils',
    version='0.3.0',
    zip_safe=False,
    entry_points={
        "console_scripts":[
            'panw-utils=panw_utils.panw_utils:main',
            'get-panw-api-key=panw_utils.get_panw_api_key:main',
            'get-panw-firewalls=panw_utils.get_panw_firewalls:main',
            'get-panw-interfaces=panw_utils.get_panw_interfaces:main',
            'get-panw-config=panw_utils.get_panw_config:main',
        ]
    },
)
