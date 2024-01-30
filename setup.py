#!/usr/bin/env python
from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

requires = [
    "snowflake-sqlalchemy>=1.1.10",
    "snowflake-connector-python[pandas]>=2.7.8",
    "pandas>=0.25.3",
    "pyyaml==6.0.0",
    "pygsheets==2.0.5",
]


setup(
    name="amberdata",
    version="0.1.1",
    author="Amber Strategy Data",
    author_email="amber.strategy.data@gmail.com",
    description="Amber Data Utils",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/strategydata/amber-data-utils",
    packages=find_packages(),
    install_requires=requires,
)
