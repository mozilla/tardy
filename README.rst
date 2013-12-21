A library for interfacing with Stackato and for automatically updating
stackato instances. This is specifically built for Mozilla and Stackato and
might not be relevant to you.

*This is very much a work in progress*.

To install::

  pip install tardy

Tardy is a Python library with a command line interface.

* ``-f`` or ``--file``: points to a JSON file that contains configuration.

* ``-d`` or ``--dump``: dumps the contents of the Tardy configuration (which is
  just a JSON file) that contains a list of all the instances created by Tardy.

* ``-t`` or ``--test``: doesn't actually execute commands, just prints.

* ``-g`` or ``--git``: used when you aren't running Tardy from the source of the
  project. It will create a ``.tardy.repos`` directory and check the source out
  into that directory. This is used when you have one project that requires
  two or three other projects.

* ``-l`` or ``--last``: prints out the uuid of the last stackato instance created
  for that project.

* ``-a`` or ``--action``: one of ``update``, ``delete``, ``create``, ``restart``. Will do:

  * ``create``: creates an instance and stores into the Tardy configuration.

  * ``update``: ssh's into each stackato instance and does a git pull then
    restarts the instance.

  * ``restart``: stops and starts each stackato instance.

  * ``delete``: deletes each stackato instance.

For each stackato instance you want to create, you will need a configuration
file::

  {
    "stackato": {
      "name": "zippy",
      "pre": [
        "cp lib/config/local-dist.js lib/config/local.js"
      ],
      "git": {
        "repo": "https://github.com/mozilla/zippy.git"
      }
    },
    "git": {
      "name": "zippy",
      "repo": "https://github.com/mozilla/zippy.git"
    }
  }

* ``stackato``: config for stackato

  * ``pre``: a list of commands to run prior to upload to stackato, each command
    is passed the env variables as dictionary for python strings. The variable
    ``URL`` is also passed, this is the stackato URL instance.

  * ``git``: the git repo of this instance.

* ``git``: config for git

  * ``repo``: the git repo of this instance.

Examples
--------

Creating an integration test between two services
=================================================

In this case we have a repo that contains integration tests between two other
repos. This will create a unique instance of each repo on stackato and then run
the integration tests. Since the instances are unique, multiple people can run
this at once::

  # Create a zippy instance.
  tardy -f zippy.json -a create -g

  # Find the last instance of zippy so solitude can find it.
  zippy=`tardy -f zippy.json --last`
  echo 'Last instance of zippy is at:' $zippy
  export ZIPPY=$zippy

  # Create a solitude instance, pointing to zippy.
  tardy -f solitude.json -a create -g

  # Now run the zippy solitude integration tests.
  solitude=`tardy -f solitude.json --last`
  echo 'Last instance of solitude is at:' $solitude
  python zippy-basic.py --url=https://solitude-$solitude.paas.allizom.org

  # Get rid of our solitude and zippy instances
  tardy -f solitude.json -a delete -g
  tardy -f zippy.json -a delete -g

For more see https://github.com/andymckay/solitude-zippy

Updating stackato when unit tests pass
======================================

In this case we are checking out a repo and running unit tests on a repo. This
will occur on each github commit. If the tests pass then it will update the
instance on stackato::

  source /opt/rh/python27/enable
  set -e

  cd $WORKSPACE
  VENV=$WORKSPACE/venv

  if [ ! -d "$VENV/bin" ]; then
    echo "No virtualenv found.  Making one..."
    virtualenv $VENV --system-site-packages --python=python
    source $VENV/bin/activate
    pip install --upgrade pip
  fi

  source $VENV/bin/activate
  pip install --upgrade tardy

  # In this case the jenkins user has stackato credentials to hit the server.
  tardy -f tardy.json -a upgrade

For more see https://github.com/mozilla/zippy
