'''the wastedyears database interface'''

from __future__ import annotations
import datetime
import os
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import event

from . import config, models


def open_db(cfg: config.Config) -> WastedYearsDB:
    cfg.create_data_dir()
    engine = create_engine(cfg.db_url)
    return WastedYearsDB(engine.connect())


def nuke_db(cfg: config.Config):
    prefix = 'sqlite:///'
    if cfg.db_url.startswith(prefix):
        filename = cfg.db_url[len(prefix):]
        try:
            os.remove(filename)
        except FileNotFoundError:
            pass
        return

    raise RuntimeError(f'cannot nuke database: {cfg.db_url}')


def create_engine(db_url: str) -> sa.engine.base.Engine:
    engine = sa.create_engine(db_url)
    engine = engine.execution_options(autocommit=False)
    event.listen(
        engine,
        'connect',
        lambda conn, conn_record: conn.execute('pragma foreign_keys=on'),
    )

    # make sure it actually works
    with engine.connect():
        pass

    return engine


class WastedYearsDB:
    metadata = sa.MetaData()
    tbl_tasks = sa.Table(
        'tasks',
        metadata,
        sa.Column('task_id', sa.Integer, primary_key=True),
        sa.Column('update_ts', sa.DateTime, nullable=False),
        sa.Column('start_ts', sa.DateTime, nullable=False),
        sa.Column('end_ts', sa.DateTime, nullable=True),
        sa.Column('description', sa.Text, nullable=False),
    )
    tbl_words = sa.Table(
        'words',
        metadata,
        sa.Column('word_id', sa.Integer, primary_key=True),
        sa.Column('word', sa.String, unique=True),
        sa.Column('total_elapsed', sa.Integer),
    )

    # association table, so we can update words when we delete/modify an
    # existing task
    tbl_task_words = sa.Table(
        'task_words',
        metadata,
        sa.Column('task_id', sa.Integer, sa.ForeignKey('tasks.task_id')),
        sa.Column('word_id', sa.Integer, sa.ForeignKey('words.word_id')),
        sa.UniqueConstraint('task_id', 'word_id'),
    )

    conn: sa.engine.base.Connection
    txn: Optional[sa.engine.base.Transaction]

    def __init__(self, conn: sa.engine.base.Connection):
        self.conn = conn
        self.txn = conn.begin()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        if self.txn is not None:
            self.txn.__exit__(type_, value, traceback)
        self.close()

    def close(self):
        self.conn.close()

    def begin(self):
        """Begin a new transaction."""
        assert self.txn is None, 'a transaction is already open'
        self.txn = self.conn.begin()

    def commit(self):
        """Commit the current transaction."""
        assert self.txn is not None
        self.txn.commit()
        self.txn = None

    def init_schema(self):
        self.metadata.create_all(bind=self.conn)

    def end_last_task(self, end_ts: datetime.datetime):
        '''update the most recently added task: set end_ts, if not already set'''
        sql = ('update tasks set end_ts = ? ' +
               'where end_ts is null and task_id in '
               '(select task_id from tasks order by task_id desc limit 1)')
        self.conn.execute(sql, (end_ts,))

    def add_task(self, task: models.Task) -> int:
        words = models.split_description(task.description)
        new_words = self.upsert_words(words)

        insert = (
            self.tbl_tasks
            .insert()
            .values(
                update_ts=sa.text('datetime()'),
                start_ts=task.start_ts,
                end_ts=task.end_ts,
                description=task.description))
        result = self.conn.execute(insert)
        task_id = result.inserted_primary_key[0]
        assert isinstance(task_id, int)

        word_ids: set[int] = set(new_words.values())
        lookup = set(words) - new_words.keys()
        if lookup:
            select = self.tbl_words.select().where(self.tbl_words.c.word.in_(lookup))
            rows = self.conn.execute(select)
            for row in rows:
                word_ids.add(row.word_id)

        insert = self.tbl_task_words.insert()
        values = [{'task_id': task_id, 'word_id': word_id}
                  for word_id in word_ids]
        self.conn.execute(insert, values)

        return task_id

    def upsert_words(self, words: list[str]) -> dict[str, int]:
        '''Insert words that are not already in the database.
        Ignore words that are there.

        Return a map of word to word_id for newly inserted words.
        '''
        if not words:
            return {}

        sql = ('insert into words (word) values ' +
               ', '.join(['(?)'] * len(words)) +
               'on conflict do nothing '
               'returning word, word_id')

        result = self.conn.execute(sql, tuple(words))
        return {row.word: row.word_id for row in result}

    def list_tasks(self):
        stmt = self.tbl_tasks.select()
        rows = self.conn.execute(stmt)
        return [self.load_task(row) for row in rows]

    def load_task(self, row) -> models.Task:
        task = models.Task(**row)

        # SQLite has no knowledge of timezones, but we always write
        # datetimes to the database in UTC. Make that explicit on the way
        # back in.
        for (attr, val) in vars(task).items():
            if isinstance(val, datetime.datetime) and val.tzinfo is None:
                val = val.replace(tzinfo=datetime.timezone.utc)
                setattr(task, attr, val)

        return task
