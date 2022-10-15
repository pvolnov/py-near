from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="async_near",
    author_email="petr@herewallet.app",
    url="https://github.com/here-wallet/async_near",
    packages=find_packages(include=["async_near", "async_near.exceptions"]),
    version="1.0.10",
    description="Near async rpc client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Petr Volnov",
    license="MIT",
    install_requires=["base58", "ed25519", "aiohttp"],
)
