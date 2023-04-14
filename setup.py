from setuptools import setup, find_packages

setup(
    packages=find_packages(),
    package_dir={'api': 'api', 'esddns_service': 'esddns_service'}
)