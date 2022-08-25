#!/usr/bin/env python

from setuptools import setup

setup(name='tap-toast',
      version='0.1.2',
      description='Singer.io tap for extracting data from the Client API',
      author='@lambtron',
      url='https://andyjiang.com',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_toast'],
      install_requires=[
          'singer-python',
          'requests',
          'backoff',
          'jsonpath_ng'
      ],
      entry_points='''
          [console_scripts]
          tap-toast=tap_toast:main
      ''',
      packages=['tap_toast'],
      package_data={
          'tap_github': [
              'tap_github/schemas/*.json',
              'tap_github/metadatas/*.json',
              'tap_github/postman/*.json'
          ]
      },
      include_package_data=True
)
