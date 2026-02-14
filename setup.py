from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mailchk",
    version="1.0.0",
    author="Mailchk",
    author_email="support@mailchk.io",
    description="Official Python SDK for Mailchk email validation API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mailchk/mailchk-python",
    project_urls={
        "Bug Tracker": "https://github.com/mailchk/mailchk-python/issues",
        "Documentation": "https://mailchk.io/docs",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Email",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "async": ["aiohttp>=3.8.0"],
        "dev": ["pytest", "pytest-asyncio", "responses"],
    },
)
