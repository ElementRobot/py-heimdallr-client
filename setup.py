from setuptools import setup, find_packages

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='py-heimdallr-client',
    version='0.0.1',
    description='Python API for Heimdallr',
    long_description=long_description,
    url='https://github.com/ElementRobot/py-heimdallr-client',
    author='Element Robot LLC',
    author_email='dev@elementrobot.co',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',

        # Supported Python Versions
        'Programming Language :: Python :: 2.6',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools'
    ],
    keywords=['heimdallr', 'rtc', 'websockets'],
    packages=find_packages(exclude=['tests/*']),
    install_requires=[
        'socketIO-client-2',
        'wrapt',
        'pyasn1'
    ],
    test_suite='tests',
    tests_require=['coverage'],
    scripts=['bin/post-schemas']
)