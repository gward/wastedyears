'''wastedyears configuration data'''

import os


def get_config():
    '''return a Config object ready to use'''
    return Config()


class Config:
    '''An object that encapsulates all config settings for wastedyears.

    No config file support implemented yet, so everything is hardcoded.
    '''
    data_dir: str
    db_url: str

    def __init__(self):
        # from https://specifications.freedesktop.org/basedir-spec/basedir-spec-0.6.html
        data_home = os.environ.get(
            'XDG_DATA_HOME',
            os.path.join(os.environ['HOME'], '.local', 'share'))

        self.data_dir = os.path.join(data_home, 'wastedyears')
        self.db_url = 'sqlite:///' + os.path.join(self.data_dir, 'wastedyears.sqlite3')

    def create_data_dir(self):
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)
