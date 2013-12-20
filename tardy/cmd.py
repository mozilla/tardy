import argparse

from lib import Config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', required=True)
    parser.add_argument('-u', '--update', action='store_true')
    result = parser.parse_args()

    config = Config(filename=result.file)
    if result.update:
        config.stackato.update()
    else:
        config.stackato.push()
        config.stackato.delete()
