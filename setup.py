#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from setuptools import setup

import mishmash


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

def find_packages(path, src):
    packages = []
    for pkg in [src]:
        for _dir, subdirectories, files in (
                os.walk(os.path.join(path, pkg))):
            if '__init__.py' in files:
                tokens = _dir.split(os.sep)[len(path.split(os.sep)):]
                packages.append(".".join(tokens))
    return packages

dist = setup(
    name=mishmash.__projectname__,
    version=mishmash.__version__,
    description='A music database using Python and SQLAlchemy.',
    long_description=readme + '\n\n' + history,
    author=mishmash.__author__,
    author_email=mishmash.__email__,
    url=mishmash.__web__,
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
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    scripts=['bin/mishmash'],
)

