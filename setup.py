#!/usr/bin/env python3
"""setup.py for thankyouai CLI.

Install: pip install -e .
"""

from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="thankyouai",
    version="0.1.0",
    author="ThankYou AI",
    author_email="",
    description="CLI for ThankYou AI — async image, audio, and video generation. Requires: TY_KEY",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/39-ai/thankyouai-cli",
    packages=find_packages(exclude=["tests*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "responses>=0.25.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "thankyouai=thankyouai.cli:main",
        ],
    },
    zip_safe=False,
)
