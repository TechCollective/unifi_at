#!/usr/bin/env python

from setuptools import setup

setup(name='unifi_at',
      version='0.01',
      description='scripts to integrate Autotask and a UniFi Controller',
      author='Jeffrey Brite',
      author_email='jeff@techcollective.com',
      url='https://github.com/TechCollective/unifi_at',
      packages=['unifi_at'],
      scripts=['ci2unifi.py'],
      classifiers=[],
      install_requires=['requests', 'macaddress'],
      )
