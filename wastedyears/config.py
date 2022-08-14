'''wastedyears configuration data'''

from __future__ import annotations

import configparser
import dataclasses
import os


def get_config() -> Config:
    '''return a Config object ready to use'''
    defaults = get_default_config()
    parser = configparser.ConfigParser()

    config_home = _xdg_dir('XDG_CONFIG_HOME', '.config')

    parser.read_string(defaults)
    parser.read(os.path.join(config_home, 'wastedyears.cfg'))

    return Config(
        data_dir=parser.get('core', 'data_dir'),
        db_url=parser.get('core', 'db_url'),
    )


def get_default_config() -> str:
    '''return a hardcoded default config'''
    # from https://specifications.freedesktop.org/basedir-spec/basedir-spec-0.6.html
    data_home = _xdg_dir('XDG_DATA_HOME', '.local', 'share')

    return f'''[core]
data_dir={os.path.join(data_home, 'wastedyears')}
db_url=sqlite:///%(data_dir)s/wastedyears.sqlite
'''


def _xdg_dir(env_var, *default_path):
    return os.environ.get(
        env_var,
        os.path.join(os.environ['HOME'], *default_path))


@dataclasses.dataclass
class Config:
    '''An object that encapsulates all config settings for wastedyears.

    No config file support implemented yet, so everything is hardcoded.
    '''
    data_dir: str
    db_url: str

    def create_data_dir(self):
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)
