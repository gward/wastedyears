'''wastedyears, the command-line interface'''

import datetime
import sys
from typing import Tuple

import click

from . import config, models, database


class AliasedGroup(click.Group):
    aliases = {
        't': 'task',
        'ls': 'ls-tasks',
    }

    def list_commands(self, ctx):
        # return a more sensible order (not alphabetical)
        return [
            'init',
            'task',
            'ls-tasks',
            'ingest',
        ]

    def get_command(self, ctx, cmd_name):
        cmd_name = self.aliases.get(cmd_name, cmd_name)
        return super().get_command(ctx, cmd_name)


@click.group(cls=AliasedGroup)
def main():
    pass


@main.command()
def init():
    '''initialize wastedyears (database only -- no config file yet)'''
    cfg = config.get_config()
    with database.open_db(cfg) as db:
        db.init_schema()


@main.command()
def nuke():
    '''destroy the database (no takebacks)'''
    cfg = config.get_config()
    database.nuke_db(cfg)


@main.command()
@click.argument('taskword', nargs=-1)
def task(taskword: Tuple[str]):
    '''start a new task (and mark the previous one done)'''
    cfg = config.get_config()

    now = _now()
    taskwords = list(taskword)
    if taskwords:
        task = models.Task(start_ts=now, description=' '.join(taskwords))
    else:
        task = _run_editor()

    with database.open_db(cfg) as db:
        db.end_last_task(now)
        db.add_task(task)


@main.command()
def done():
    '''mark the current task done without starting a new one'''
    cfg = config.get_config()
    with database.open_db(cfg) as db:
        db.end_last_task(_now())


def _run_editor():
    raise NotImplementedError()


@main.command('ls-tasks')
def list_tasks():
    '''list all tasks in the database'''
    cfg = config.get_config()
    with database.open_db(cfg) as db:
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
    '''read old tasks from a text file into the database'''
    from . import ingest as ingest_

    cfg = config.get_config()
    with database.open_db(cfg) as db:
        for task in ingest_.ingest(db, infile):
            print(task)
            db.add_task(task)


def _now() -> datetime.datetime:
    '''return current time, in UTC, truncated to second'''
    now = datetime.datetime.utcnow()
    now = now.replace(microsecond=0)
    return now


if __name__ == '__main__':
    main()
