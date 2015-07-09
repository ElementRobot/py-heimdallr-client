from setuptools import setup, find_packages

setup(
    name='py-heimdallr-client',
    version='0.0.0',
    description='Python API for Heimdallr',
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
    keywords='heimdallr rtc websockets',
    packages=find_packages(exclude=['tests/*']),
    install_requires=[
        'socketIO-client',
        'wrapt',
        'pyopenssl',
        'ndg-httpsclient',
        'pyasn1'
    ]
)