import argparse
import pprint

from lib import Config, Storage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', default='tardy.json')
    parser.add_argument('-d', '--dump', action='store_true')
    parser.add_argument('-a', '--action')
    parser.add_argument('-t', '--test', action='store_true')
    parser.add_argument('-g', '--git', action='store_true')
    parser.add_argument('-l', '--last', action='store_true')
    parser.add_argument('-n', '--nocolour', action='store_true')
    parser.add_argument('-q', '--quiet', action='store_true')
    result = parser.parse_args()

    if result.dump:
        storage = Storage()
        print 'Dumping:', storage.filename
        storage.load()
        pprint.pprint(storage.data)
        return

    if result.last:
        storage = Storage()
        storage.load()
        print storage.data[result.file]['apps'][-1]
        return

    choices = ['update', 'delete', 'create', 'restart']
    if result.action not in choices:
        raise ValueError('--action must be one of %s' % ','.join(choices))

    if not result.file:
        raise ValueError('--file must be specified')

    config = Config(filename=result.file, test=result.test,
                    colour=result.nocolour, quiet=result.quiet)
    if result.git:
        config.git.clone()
        config.stackato.cwd = config.git.repo

    try:
        getattr(config.stackato, result.action)()
    finally:
        config.save()
