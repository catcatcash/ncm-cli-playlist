#!/usr/bin/env python3
from setuptools import find_namespace_packages, setup

setup(
    name="cli-anything-ncm-playlist",
    version="0.1.0",
    author="catcatcash",
    description="CLI-Anything-style NetEase Cloud Music playlist management",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/catcatcash/ncm-cli-playlist",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    python_requires=">=3.10",
    install_requires=["click>=8.0" , "requests>=2.28"],
    extras_require={"dev": ["pytest>=7.0"]},
    entry_points={
        "console_scripts": [
            "cli-anything-ncm-playlist=cli_anything.ncm_playlist.ncm_playlist_cli:main",
        ]
    },
    include_package_data=True,
    zip_safe=False,
)
