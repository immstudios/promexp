import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "promexp",
    version = "1.0.2",
    author = "Martin Wacker",
    author_email = "martas@imm.cz",
    description = "A simple system metrics exporter for Prometheus",
    license = "MIT",
    keywords = "metrics devops prometheus",
    url = "https://github.com/immstudios/promexp",
    packages=['promexp', 'promexp.providers', 'promexp.providers.casparcg'],
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Utilities",
    ],
)
