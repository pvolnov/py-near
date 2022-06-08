from setuptools import find_packages, setup

setup(
    name='async_near',
    packages=find_packages(include=['async_near']),
    version='0.1.1',
    description='Near async rpc client',
    author='Petr Volnov',
    license='MIT',
    install_requires=['base58', 'ed25519', 'aiohttp'],
)