"""Setup."""

import sys
from setuptools import setup, find_packages

with open("capella/__init__.py") as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

with open("README.md") as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = [
    "click",
    "rasterio>=1.0.28",
    "shapely",
    "aiohttp",
    "numpy~=1.15"
]

setup(
    name="rio-capella",
    version=version,
    description=u"CLI for ordering Capella Space SAR data",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="Capella SAR rasterio",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    install_requires=inst_reqs,
    entry_points="""
      [rasterio.rio_plugins]
      capella-order=capella.scripts.cli:capella_order
      """,
)
