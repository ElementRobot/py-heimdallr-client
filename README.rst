This module is a Python API for `Heimdallr <https://heimdallr.co/>`__.

Installation
------------

``pip install py-heimdallr-client``

Contributing
------------

Please use a linter to help follow PEP8 style guidelines. We use Vincent
Driessen's
`git-flow <http://nvie.com/posts/a-successful-git-branching-model/>`__
so please make pull requests to the develop branch. For any new features
you might add please add the corresponding documentation and tests. To
setup the project for development you need
`virtualenv <https://virtualenv.pypa.io/en/stable/>`__. Once you have
virtualenv installed and setup can run:

::

    mkvirtualenv py-heimdallr-client
    workon py-heimdallr-client
    git clone git@github.com:Layer3DLab/py-heimdallr-client.git
    cd py-heimdallr-client
    git checkout develop
    npm install
    pip install -r dev_requirements.txt

NOTE: if you're on OSX and cryptography fails to install you may need to
follow these
`directions <https://cryptography.io/en/latest/installation/#building-cryptography-on-os-x>`__.

Adding Documentation
~~~~~~~~~~~~~~~~~~~~

We use `Sphinx <http://www.sphinx-doc.org/en/stable/index.html>`__ with
the autodoc and napoleon extensions to generate the documentation for
this module. So to add documentation simply add Python docstrings to
whatever classes, methods, etc. that you add. We use Google style
docstrings (examples
`here <http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`__).
To build the docs run the following from the project directory:

::

    cd docs
    make html

Adding Tests
~~~~~~~~~~~~

We use `unittest <https://docs.python.org/2.7/library/unittest.html>`__
for our testing suite. To run the tests you can just call
``python setup.py test`` from the project directory. To run them
directly you can just call ``python tests/__init__.py`` To run coverage
tests and generate an HTML report run:

::

    coverage  run --source="./heimdallr_client" --branch -m unittest tests
    coverage html
