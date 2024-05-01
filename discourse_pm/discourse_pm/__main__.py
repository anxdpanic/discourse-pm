import argparse
import logging
from pathlib import Path

from . import __logger__
from .config import Config
from .discourse import Discourse

logger = logging.getLogger(__logger__)


def enable_logging():
    global logger

    def _logger_configured():
        for _handler in logger.handlers:
            if isinstance(_handler, logging.StreamHandler):
                return True
        return False

    logging_format = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if not _logger_configured():
        logger.setLevel(level=logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging_format)
        logger.addHandler(handler)


def client():
    config = Config().config
    return Discourse(config['hostname'], config['username'], config['api_key'])


def read_message_file(filename):
    if not filename.is_file():
        raise FileNotFoundError(f'{filename} does not exist')
    return filename.read_text()


def pm_single(username, title, message, filename):
    if filename:
        message = read_message_file(filename)
    client().pm(username, title, message)


def pm_multi(usernames, title, message, filename):
    if filename:
        message = read_message_file(filename)
    usernames = usernames.split(',')
    client().pm_users(usernames, title, message)


def pm_all(title, message, filename):
    if filename:
        message = read_message_file(filename)
    client().pm_all(title, message)


def pm_moderators(title, message, filename):
    if filename:
        message = read_message_file(filename)
    client().pm_moderators(title, message)


def main():
    enable_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--title', dest='title', help='Title of the PM')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--message', dest='message', help='Body of the PM')
    group.add_argument('-f', '--file', dest='filename', type=Path,
                       help='Body of the PM, read from the provided file')

    subparsers = parser.add_subparsers(dest='subparser')

    parser_single = subparsers.add_parser('pm_single')
    parser_single.add_argument('-u', '--username', dest='username', help='Username to PM')

    parser_multi = subparsers.add_parser('pm_multi')
    parser_multi.add_argument('-u', '--usernames', dest='usernames', help='List of usernames to PM')

    subparsers.add_parser('pm_all')
    subparsers.add_parser('pm_moderators')

    kwargs = vars(parser.parse_args())
    globals()[kwargs.pop('subparser')](**kwargs)


if __name__ == '__main__':
    main()
