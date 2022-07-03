'''the wastedyears database interface'''

import datetime

import sqlalchemy as sa
from sqlalchemy import event, exc as saexc

from . import config, models


def open_db(cfg: config.Config):
    cfg.create_data_dir()
    engine = sa.create_engine(cfg.db_url)
    engine = engine.execution_options(autocommit=False)
    event.listen(
        engine,
        'connect',
        lambda conn, conn_record: conn.execute('pragma foreign_keys=on'),
    )

    try:
        with engine.connect():
            pass
    except saexc.OperationalError as err:
        print('db_url:', cfg.db_url)
        raise err

    return WastedYearsDB(engine)


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
        sa.Column('last_task_id', sa.Integer),
        sa.Column('word', sa.String),
    )

    def __init__(self, engine: sa.engine.base.Engine):
        self.engine = engine
        self.conn = engine.connect()
        self.txn = None

    def close(self):
        self.conn.close()

    def begin(self):
        """Begin a new transaction."""
        self.txn = self.conn.begin()

    def commit(self):
        """Commit the current transaction."""
        assert self.txn is not None
        self.txn.commit()
        self.txn = None

    def init_schema(self):
        self.metadata.create_all(self.engine)

    def end_last_task(self, end_ts: datetime.datetime):
        '''update the most recently added task: set end_ts, if not already set'''
        sql = ('update tasks set end_ts = ? ' +
               'where end_ts is null and task_id in '
               '(select task_id from tasks order by task_id desc limit 1)')
        self.conn.execute(sql, (end_ts,))

    def add_task(self, task: models.Task):
        stmt = (self.tbl_tasks
                .insert()
                .values(
                    update_ts=sa.text('datetime()'),
                    start_ts=task.start_ts,
                    end_ts=task.end_ts,
                    description=task.description))
        self.conn.execute(stmt)
