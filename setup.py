#!/usr/bin/env python

from setuptools import setup

setup(name='tap-toast',
      version='0.1.2',
      description='Singer.io tap for extracting data from the Toast API',
      author='@lambtron',
      url='https://andyjiang.com',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_toast'],
      install_requires=[
          'singer-python==5.9.0',
          'requests==2.21.0',
          'backoff==1.8.0',
          'jsonpath_ng==1.5.3'
      ],
      entry_points='''
          [console_scripts]
          tap-toast=tap_toast:main
      ''',
      packages=['tap_toast'],
      include_package_data=True,
)
