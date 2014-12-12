#!/usr/bin/env python
# coding=utf-8

from setuptools import setup
from gitversion import get_version

setup(
    name='pydaqflex',
    version=get_version(),
    description='Python port of the Measurement Computing DAQFlex framework',
    author='David Kiliani',
    author_email='mail@davidkiliani.de',
    url='https://github.com/torfbolt/PyDAQFlex',
    packages=['daqflex'],
    package_data={'daqflex': ['firmware/*.rbf']},
    long_description=open('README.rst', 'rt').read(),
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='mmc daqflex measurement computing usb driver',
    license='BSD',
    install_requires=[
                      'setuptools',
                      'pyusb',
    ],
)

