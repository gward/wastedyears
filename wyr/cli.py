'''wastedyears, the command-line interface'''

from typing import Tuple

import click
import datetime

from . import config, models, database


@click.group
def main():
    pass


@main.command()
def init():
    '''initialize wastedyears (database only -- no config file yet)'''
    cfg = config.get_config()
    db = database.open_db(cfg)
    db.init_schema()
    db.close()
    print('database initialized:', db)


@main.command()
@click.argument('taskword', nargs=-1)
def task(taskword: Tuple[str]):
    cfg = config.get_config()

    now = datetime.datetime.utcnow()
    taskwords = list(taskword)
    if taskwords:
        task = models.Task(start_ts=now, description=' '.join(taskwords))
    else:
        task = _run_editor()

    db = database.open_db(cfg)
    db.begin()
    db.end_last_task(now)
    db.add_task(task)
    db.commit()
    db.close()


def _run_editor():
    raise NotImplementedError()


if __name__ == '__main__':
    main()
