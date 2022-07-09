'''wastedyears, the command-line interface'''

import datetime
import sys
from typing import Tuple

import click

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
    now = now.replace(microsecond=0)    # truncate to nearest second
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


@main.command('ls-tasks')
def list_tasks():
    cfg = config.get_config()
    db = database.open_db(cfg)
    tasks = db.list_tasks()

    for task in tasks:
        if task.start_ts is None:
            print(f'warning: invalid task {task.task_id} in database ' +
                  '(start_ts not set)',
                  file=sys.stderr)
            continue

        date = task.start_ts.strftime('%Y-%m-%d')
        start_time = task.start_ts.strftime('%H:%M:%S')
        end_time = '   --   '
        if task.end_ts is not None:
            end_time = task.end_ts.strftime('%H:%M:%S')

        print(f'{date}: {start_time} … {end_time}: {task.description}')


@main.command('ingest')
@click.argument('infile', type=click.File('rt'))
def ingest(infile):
    from . import ingest as ingest_

    cfg = config.get_config()
    db = database.open_db(cfg)
    ingest_.ingest(db, infile)


if __name__ == '__main__':
    main()
