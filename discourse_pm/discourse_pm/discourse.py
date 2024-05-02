import json
import logging
import time
from copy import deepcopy
from functools import wraps
from pathlib import Path

import requests

from . import __logger__

logger = logging.getLogger(__logger__)

sleep_between_request = 1
max_users_per_message = 50


def rate_limit(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        rate_limited = True
        response = None
        while rate_limited:
            rate_limited = False
            response = method(self, *method_args, **method_kwargs)
            logger.debug(f'|{method.__name__}| HTTP Request: {response.status_code} {response.reason}')
            payload = response.json()
            for error in payload.get('errors', []):
                logger.error(f'|{method.__name__}| HTTP Error: {error}')
            if response.status_code == 429:
                rate_limited = True
                wait_seconds = payload['extras'].get('wait_seconds', 10)
                logger.debug(f'|{method.__name__}| Rate limit reached, Discourse API has requested a '
                             f'{wait_seconds} second delay')
                time.sleep(wait_seconds)

        return response

    return _impl


class Data:
    def __init__(self):
        self._filename = Path(Path().cwd(), 'data.json')
        self._template = {
            'users': []
        }
        self._data = deepcopy(self._template)
        self._load()

    @property
    def data(self):
        return self._data

    @property
    def users(self):
        return self._data['users']

    def set_users(self, usernames):
        self._data['users'] = usernames
        self._save()

    def add_user(self, username):
        self._data['users'].append(username)
        self._save()

    def del_user(self, username):
        self._data['users'] = [user for user in self._data['users'] if user != username]
        self._save()

    def _save(self):
        with self._filename.open('w') as handle:
            json.dump(self._data, handle, indent=4)

    def _load(self):
        if not self._filename.is_file():
            with self._filename.open('w') as handle:
                json.dump(self._template, handle, indent=4)
            return

        try:
            self._data = json.loads(self._filename.read_text())
        except json.JSONDecodeError:
            with self._filename.open('w') as handle:
                json.dump(self._template, handle, indent=4)
            self._data = deepcopy(self._template)
            return

        if 'users' not in self._data or not isinstance(self._data['users'], list):
            with self._filename.open('w') as handle:
                json.dump(self._template, handle, indent=4)
            self._data = deepcopy(self._template)
            return


class Discourse:
    def __init__(self, hostname, username, api_key):
        self._hostname = hostname
        self._username = username
        self._api_key = api_key
        self._headers = {
            'Api-Key': self._api_key,
            'Api-Username': self._username,
            'Accept': 'application/json'
        }

    @property
    def hostname(self):
        return self._hostname

    @property
    def username(self):
        return self._username

    @property
    def api_key(self):
        return self._api_key

    @property
    def headers(self):
        return self._headers

    @staticmethod
    def _yes_no_input(prompt):
        while True:
            user_input = input(f'{prompt} [Y/n] ')
            if user_input.lower() in ['', 'y', 'yes']:
                return True
            if user_input.lower() in ['n', 'no']:
                return False
            print(f'Unrecognized input: {user_input}')

    @rate_limit
    def _api_members(self, limit, offset):
        api_users = f'https://{self.hostname}/groups/trust_level_0/members?limit={limit}&offset={offset}'
        response = requests.get(api_users, headers=self.headers)
        return response

    @rate_limit
    def _api_user_exists(self, username):
        api_user = f'https://{self.hostname}/u/{username}'
        response = requests.get(api_user, headers=self.headers)
        if 200 <= response.status_code < 300:
            logger.info(f'User {username} exists')
        elif response.status_code != 429:
            logger.info(f'User {username} does not exist')
        return response

    @rate_limit
    def _api_send_pm(self, username, title, message):
        api_posts = f'https://{self.hostname}/posts'
        data = {
            'title': title,
            'raw': message,
            'archetype': 'private_message',
            'target_recipients': username
        }
        headers = deepcopy(self.headers)
        headers['Content-Type'] = 'application/json'
        response = requests.post(api_posts, headers=headers, data=json.dumps(data))
        return response

    def _get_users(self):
        page = 0
        offset = 0
        limit = 50
        users = []
        logger.info(f'Gathering all users')
        while True:
            if page > 0:
                offset += limit

            response = self._api_members(limit, offset)
            if 300 <= response.status_code or 200 > response.status_code:
                break

            payload = response.json()
            new_users = payload.get('members', [])
            if len(new_users) == 0:
                break

            users.extend(new_users)
            logger.info(f'Added {len(new_users)} new users, '
                        f'{100 * float(len(users)) / float(payload["meta"]["total"])}% complete')

            if len(users) == payload['meta']['total']:
                break

            page += 1
            time.sleep(sleep_between_request)

        logger.info(f'Gathered a total of {len(users)} users')
        return users

    def _send_pm(self, username, title, message):
        response = self._api_send_pm(username, title, message)
        logger.info(f'Sending PM to {username}: {response.status_code} {response.reason}')
        return 200 <= response.status_code < 300

    def _pm_users(self, users, title, message, data=None):
        last_item_index = len(users) - 1
        for index, user in enumerate(users):
            self._send_pm(user, title, message)
            if isinstance(data, Data):
                data.del_user(user)
            if index != last_item_index:
                time.sleep(sleep_between_request)

    def pm(self, username, title, message):
        if self._api_user_exists(username):
            self._send_pm(username, title, message)

    def pm_all(self, title, message):
        data = Data()
        answer = False
        if len(data.users) > 0:
            answer = self._yes_no_input('Found users from a previous run, continue previous run?')
        if answer:
            users = data.users
        else:
            users = [user['username'] for user in self._get_users()]
            data.set_users(users)
        self._pm_users(users, title, message, data=data)

    def pm_moderators(self, title, message):
        moderators = [user['username'] for user in self._get_users() if user.get('moderator', False)]
        self._pm_users(moderators, title, message)

    def pm_users(self, usernames, title, message):
        last_item_index = len(usernames) - 1
        for index, username in enumerate(usernames):
            if self._api_user_exists(username):
                self._send_pm(username, title, message)
                if index != last_item_index:
                    time.sleep(sleep_between_request)
