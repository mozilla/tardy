import argparse
import json
import os
import subprocess
import time
import uuid

domain = 'paas.allizom.org'


def cmd(command):
    command = 'stackato %s' % command
    print 'Command:', command
    start = time.time()
    res = subprocess.check_output(command, shell=True)
    if res:
        print res
    print 'Completed in: %s' % (time.time() - start)
    print


register = {}


class Config(object):

    def __init__(self, filename=None):
        self.config = None
        self.filename = filename
        self.config = json.load(open(filename, 'r'))
        self.stackato = Stackato(self.config['stackato'])


class Stackato(object):

    def __init__(self, data):
        self.id_ = uuid.uuid4()
        self.data = data
        self.uid_ = '{0}-{1}'.format(self.data['name'], self.id_)
        self.cwd = os.getcwd()

        register[self.uid_] = {'app': False, 'services': []}

    def push(self):
        for command in self.data.get('pre', []):
            cmd(command)

        print 'Creating:', self.uid_
        cmd('push {0} --url https://{0}.{1}'
            ' --no-prompt --no-start'
            .format(self.uid_, domain))

        register[self.uid_]['app'] = True

        print 'Starting:', self.uid_
        cmd('start {0} --no-prompt --no-tail' .format(self.uid_))

        for command in self.data.get('post', []):
            cmd(command)

    def delete(self):
        print 'Stopping:', self.uid_
        cmd('stop {0}' .format(self.uid_))

        print 'Deleting:', self.uid_
        cmd('delete {1}'
            .format(self.cwd, self.uid_))

        register[self.uid_]['app'] = False

    def update(self):
        if not self.data.get('git'):
            raise ValueError('Need a value for git in the tardy config.')

        print 'Ensure git config...'
        try:
            cmd('ssh "git rev-parse"')
        except subprocess.CalledProcessError:
            # No git info, so init.
            print 'Failed, creating...'
            cmd('ssh "git init && git remote add origin {0}"'
                .format(self.data['git']))

        print 'Pulling...'
        # If people want pull to be something different got for that here.
        cmd('ssh "git {0}"'
            .format(self.data['git'].get('pull', 'pull origin master')))

        print 'Restarting...'
        cmd('stop')
        cmd('start')
