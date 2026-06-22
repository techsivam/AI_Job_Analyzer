from setuptools import setup, find_packages

with open("requirements.txt", "r") as fh:
    requirements = fh.read().splitlines()

setup(
    name="job_analyzer",
    version="0.1.0",
    author="Sivaprakash",
    packages=find_packages(),
    install_requires=requirements,
)