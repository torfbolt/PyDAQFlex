#!/usr/bin/env python

from setuptools import setup
from version import get_git_version

setup(
    name='pydaqflex',
    version=get_git_version(),
    description='Python port of the Measurement Computing DAQFlex framework',
    author='David Kiliani',
    author_email='mail@davidkiliani.de',
    #url='http://',
    py_modules=['daqflex'],
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

