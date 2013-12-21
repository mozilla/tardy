import json
import os
import shutil
import subprocess
import time
import uuid

domain = 'paas.allizom.org'

GREEN = "\033[1m\033[92m"
RED = '\033[1m\033[91m'
CYAN = '\033[1m\033[36m'
RESET = "\x1B[m"

storage_filename = '.tardy.storage.json'
repos_filename = '.tardy.repos'

class Config(object):

    def __init__(self, filename=None, test=False):
        self.config = None
        self.filename = filename
        self.config = json.load(open(filename, 'r'))
        self.storage = Storage(uid=filename)
        self.storage.load()

        self.stackato = Stackato(self.config['stackato'], self.storage)
        self.stackato.test = test

        self.git = Git(self.config['git'], self.storage)
        self.git.test = test

    def save(self):
        self.storage.save()


class Storage(object):

    def __init__(self, uid=None):
        self.filename = storage_filename
        self.data = {}
        self.uid = uid

    def load(self):
        if os.path.exists(self.filename):
            self.data = json.load(open(self.filename, 'r'))

    def save(self):
        if os.path.exists(self.filename):
            dest = '%s.backup.%s' % (self.filename, time.time())
            shutil.copy(self.filename, dest)
        json.dump(self.data, open(self.filename, 'w'))

    def get(self):
        if not self.uid in self.data:
            self.data[self.uid] = {'apps': []}
        return self.data[self.uid]


class Base(object):

    def msg(self, text):
        print
        print '%s%s:%s %s' % (CYAN, self.uid_, RESET, text)

    def cmd(self, command, prefix_override=None):
        command = '%s %s' % (prefix_override or self.cmd_prefix, command)
        print ' %sCommand: %s%s' % (GREEN, RESET, command)
        start = time.time()
        if not self.test:
            try:
                res = subprocess.check_output(command,
                    stderr=subprocess.STDOUT, shell=True)
            except subprocess.CalledProcessError, err:
                print ' {0}Command failed, output:{1} {2}'.format(
                    RED, RESET, err.output)
                raise
        else:
            res = None
        if res:
            print res
        print ' %sCompleted in:%s %ss' % (GREEN, RESET,
                                          time.time() - start)
        return res

    def json(self, command, prefix_override=None):
        command = '%s %s --json' % (prefix_override or self.cmd_prefix,
                                    command)
        print ' %sCommand: %s%s' % (GREEN, RESET, command)
        start = time.time()
        if not self.test:
            try:
                res = subprocess.check_output(command, shell=True)
            except subprocess.CalledProcessError, err:
                print '%sCommand failed, output:%s' % (RED, RESET)
                print err.output
                raise
        else:
            res = None
        print ' %sCompleted in:%s %ss' % (GREEN, RESET,
                                          time.time() - start)
        return json.loads(res)


class Git(Base):

    def __init__(self, data, storage):
        self.data = data
        self.storage = storage
        self.test = False
        self.repo = os.path.join(repos_filename, self.data['name'])
        if not os.path.exists(self.repo):
            os.makedirs(self.repo)

    @property
    def cmd_prefix(self):
        return 'cd %s; git' % self.repo

    @property
    def uid_(self):
        return self.data['name']

    def clone(self):
        self.msg('Updating repo')
        assert os.path.exists(self.repo)
        if not os.path.exists(os.path.join(self.repo, '.git')):
            self.cmd('clone %s .' % (self.data['repo']))
        else:
            self.cmd('pull origin master')


class Stackato(Base):

    def __init__(self, data, storage):
        self.id_ = None
        self.data = data
        self.cwd = os.getcwd()
        self.test = False
        self.storage = storage.get()

    @property
    def uid_(self):
        return '{0}-{1}'.format(self.data['name'], self.id_)

    @property
    def cmd_prefix(self):
        # If a clone is called, the cwd will change.
        return 'cd %s; stackato' % self.cwd

    @property
    def _cmd_data(self):
        env = os.environ.copy()
        env.update({
            'URL': 'https:\/\/{0}.{1}'.format(self.uid_, domain)
        })
        return env

    def _store(self):
        if self.test:
            return

        if self.id_ not in self.storage['apps']:
            self.storage['apps'].append(self.id_)

    def create(self):
        self.id_ = str(uuid.uuid4())
        # Store as fast as we can in case things go wrong.
        self._store()

        self.msg('Running pre creation commands')
        for command in self.data.get('pre', []):
            self.cmd(command.format(**self._cmd_data),
                     prefix_override='cd %s;' % self.cwd)

        self.msg('Creating')
        self.cmd('push {0} --url https://{0}.{1}'
                 ' --no-prompt --no-start'
                 .format(self.uid_, domain))

        self.msg('Starting')
        self.cmd('start {0} --no-prompt --no-tail' .format(self.uid_))

        for command in self.data.get('post', []):
            self.cmd(command, prefix_override='cd %s;' % self.cwd)

    def _find_services(self, data, name):
        # Iterates through the JSON and finds services bound to this instance.
        found = []
        for prov in data['provisioned']:
            if name in prov['name']:
                found.append(prov['name'])

        return found

    def delete(self):
        to_delete = []
        for id_ in self.storage['apps']:
            self.id_ = id_
            try:
                self.msg('Stopping')
                self.cmd('stop {0}' .format(self.uid_))
            except subprocess.CalledProcessError:
                self.msg('...stop failed, will try delete.')
                pass

            self.msg('Listing services')
            res = self.json('services')
            for service in self._find_services(res, self.uid_):
                self.msg('Unbinding services:')
                self.cmd('unbind-service {0} {1} --no-prompt'
                         .format(service, self.uid_))

                self.msg('Deleting services:')
                self.cmd('delete-service {0} --no-prompt'
                         .format(service))

            self.msg('Deleting')
            try:
                res = self.cmd('delete {0} --no-prompt'.format(self.uid_))
            except subprocess.CalledProcessError, err:
                if 'Application not found' in err.output:
                    self.msg('Already deleted')
                else:
                    raise

            to_delete.append(self.id_)

        for i in to_delete:
            del self.storage['apps'][self.storage['apps'].index(i)]

    def update(self):
        for id_ in self.storage['apps']:
            self.id_ = id_
            self.msg('Updating')
            if not self.data.get('git'):
                raise ValueError('Need a value for git in the tardy config.')

            self.msg('Ensure git config')
            try:
                self.cmd('ssh "git rev-parse"')
            except subprocess.CalledProcessError:
                # No git info, so init.
                self.msg('Failed, creating')
                self.cmd('ssh "git init && git remote add origin {0}"'
                         .format(self.data['git']['repo']))

            self.msg('Pulling')
            # If people want pull to be something different go for that here.
            self.cmd('ssh "git {0}"'
                     .format(self.data['git'].get('pull',
                                                  'pull origin master')))

            self._restart()

    def _restart(self):
        self.msg('Restarting')
        self.cmd('stop {0}'.format(self.uid_))
        self.cmd('start {0}'.format(self.uid_))

    def restart(self):
        for id_ in self.storage['apps']:
            self.id_ = id_
            self._restart()
