#!/usr/bin/env python

from setuptools import find_packages, setup

import chromexup


def read_file(file: str) -> str:
    with open(file) as f:
        return f.read()


setup(
    name=chromexup.__name__,
    version=chromexup.__version__,
    description=chromexup.__description__,
    long_description=read_file('README.md'),
    url=chromexup.__url__,
    author=chromexup.__author__,
    author_email=chromexup.__author_email__,
    license=chromexup.__license__,
    classifiers=[
        'Development Status :: 3 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
        'Topic :: Utilities'
    ],
    keywords='browser chrome chromium external extension updater',
    packages=find_packages(),
    install_requires=['requests'],
    entry_points={
        'console_scripts': ['chromexup = chromexup.main:main']
    },
    include_package_data=True,
    zip_safe=False,
)
