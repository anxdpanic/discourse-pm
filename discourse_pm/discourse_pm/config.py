import json
from pathlib import Path

import jsonschema


class Config:

    def __init__(self):
        self._schema = {"$schema": "http://json-schema.org/schema#", "type": "object",
                        "properties": {"hostname": {"type": "string"}, "username": {"type": "string"},
                                       "api_key": {"type": "string"}}, "required": ["api_key", "hostname", "username"]}

        self._config_file = Path(Path().cwd(), 'config.json')
        self._config = {}
        self.load()

    @property
    def schema(self):
        return self._schema

    @property
    def config_file(self):
        return self._config_file

    @property
    def config(self):
        return self._config

    def load(self):
        if not self.config_file.is_file():
            raise FileNotFoundError('config.json does not exist')

        payload = json.loads(self.config_file.read_text())
        jsonschema.validate(payload, self.schema)
        self._config = payload
