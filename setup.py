from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="py-near",
    authors=[
        {"name": "Petr Volnov", "email": "petr@herewallet.app"},
    ],
    requires_python=">=3.7",
    url="https://github.com/pvolnov/py-near",
    packages=find_packages(include=["pynear", "pynear.*"]),
    version="1.0.1",
    description="Pretty simple and fully asynchronous framework for working with NEAR blockchain",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Petr Volnov",
    documentation="Petr Volnov",
    license="MIT",
    install_requires=["base58", "ed25519", "aiohttp"],
)
