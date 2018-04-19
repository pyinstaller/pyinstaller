from setuptools import setup, find_packages

setup(
    name='nspkg4_bar',
    version='1.0.0',
    url='https://github.com/mypackage.git',
    author='Author Name',
    author_email='author@emailservice.com',
    description='Description of my package',
    packages=find_packages(),
    namespace_packages=['world'],
)
