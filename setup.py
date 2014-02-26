#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from setuptools import setup


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

install_requires = []
with open("requirements.txt") as requirements:
    for req in requirements:
        req = req.strip()
        if req and req[0] not in ('#',):
            install_requires.append(req)
print install_requires


def find_packages(path, src):
    packages = []
    for pkg in [src]:
        for _dir, subdirectories, files in (
                os.walk(os.path.join(path, pkg))):
            if '__init__.py' in files:
                tokens = _dir.split(os.sep)[len(path.split(os.sep)):]
                packages.append(".".join(tokens))
    return packages

setup(
    name='mishmash',
    version='0.1.0',
    description='Python Boilerplate contains all the boilerplate you need to create a Python package.',
    long_description=readme + '\n\n' + history,
    author='Travis Shirk',
    author_email='travis@pobox.com',
    url='https://bitbucket.org/nicfit/mishmash',
    packages=find_packages('.','mishmash'),
    include_package_data=True,
    install_requires=install_requires,
    license="GPL",
    zip_safe=False,
    keywords='mishmash',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GPL License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    test_suite='tests',
)
