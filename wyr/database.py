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
        sa.Column('word', sa.String, unique=True, nullable=False),
        sa.Column('total_count', sa.Integer, nullable=False),
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
        tbl = self.tbl_tasks
        result = self.conn.execute(
            sa.select([
                tbl.c.task_id,
                tbl.c.start_ts,
                tbl.c.end_ts,
                tbl.c.description,
            ])
            .order_by(tbl.c.task_id.desc())
            .limit(1)
        )
        row = result.fetchone()
        if row and row.end_ts is None:
            # The last task exists and is indeed unfinished.
            # Mark it finished by setting end_ts.
            result = self.conn.execute(
                tbl.update()
                .values(end_ts=end_ts)
                .where(tbl.c.task_id == row.task_id))

            # Store the words for this task (since end_ts was null, we must
            # have skipped this when the task was previously added).
            elapsed = (end_ts - row.start_ts).seconds
            words = models.split_description(row.description)
            self.upsert_words(row.task_id, words, elapsed)

    def add_task(self, task: models.Task) -> int:
        # Unconditionally insert the task itself.
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

        if task.end_ts is not None:
            # If the end time is known, that's enough to insert/update
            # the words in the task. If not, wait until end_last_task().
            assert task.start_ts is not None
            elapsed = (task.end_ts - task.start_ts).seconds

            words = models.split_description(task.description)
            self.upsert_words(task_id, words, elapsed)

        return task_id

    def upsert_words(
            self,
            task_id: int,
            words: list[str],
            elapsed: int,
    ) -> dict[str, int]:
        '''Insert words that are not already in the database.
        Ignore words that are there.

        Return a map of word to word_id for newly inserted words.
        '''
        if not words:
            return {}

        new_words: dict[str, int] = {}

        # Cannot use sqlalchemy.dialect.sqlite.insert() here: it does not
        # support '.returning()'.
        upsert = (
            'insert into words (word, total_count, total_elapsed) values ' +
            ' (?, ?, ?)' +
            ' on conflict do nothing' +
            ' returning word, word_id')
        for word in words:
            result = self.conn.execute(upsert, (word, 1, elapsed))
            row = result.fetchone()
            if row:
                new_words[row.word] = row.word_id

        tbl = self.tbl_words
        old_words = set(words) - new_words.keys()
        for word in old_words:
            self.conn.execute(
                tbl.update()
                .values(
                    total_count=sa.text('total_count + 1'),
                    total_elapsed=tbl.c.total_elapsed + elapsed,
                )
                .where(tbl.c.word == word),
            )

        # Update task_words to associate all words with task_id.
        word_ids: set[int] = set(new_words.values())
        existing_words = set(words) - new_words.keys()
        if existing_words:
            rows = self.conn.execute(
                tbl
                .select()
                .where(tbl.c.word.in_(existing_words))
            )
            for row in rows:
                word_ids.add(row.word_id)

        insert = self.tbl_task_words.insert()
        values = [{'task_id': task_id, 'word_id': word_id}
                  for word_id in word_ids]
        self.conn.execute(insert, values)

        return new_words

    def list_tasks(self):
        stmt = self.tbl_tasks.select()
        rows = self.conn.execute(stmt)
        return [self.load_task(row) for row in rows]

    def get_task_dates(self) -> list[datetime.datetime]:
        '''return the list of distinct dates on which a task started'''
        tbl = self.tbl_tasks
        result = self.conn.execute(
            sa.select([
                # SQLite's date() function truncates a datetime to a date.
                sa.distinct(sa.func.date(tbl.c.start_ts, type_=sa.Date)),
            ])
            .order_by(tbl.c.start_ts)
        )
        return [row[0] for row in result]

    def list_words(self, order_by: str) -> list[models.WordInfo]:
        tbl = self.tbl_words
        order_map = {
            'i': tbl.c.word_id,
            'w': tbl.c.word,
            'c': tbl.c.total_count.desc(),
            'e': tbl.c.total_elapsed.desc(),
        }
        order_cols = []
        for letter in order_by:
            order_cols.append(order_map[letter])

        columns = [
            tbl.c.word_id,
            tbl.c.word,
            tbl.c.total_count,
            tbl.c.total_elapsed,
        ]

        result = self.conn.execute(
            sa.select(columns).order_by(*order_cols))
        return [models.WordInfo(**row) for row in result]

    def get_word_report(
            self,
            start_ts: datetime.datetime,
            end_ts: datetime.datetime) -> dict[str, models.WordInfo]:
        result = self.conn.execute(
            sa.select([
                self.tbl_tasks.c.start_ts,
                self.tbl_tasks.c.end_ts,
                self.tbl_task_words.c.word_id,
                self.tbl_words.c.word,
            ])
            .select_from(
                self.tbl_tasks
                .join(self.tbl_task_words)
                .join(self.tbl_words)
            )
            .where(sa.and_(
                self.tbl_tasks.c.start_ts >= start_ts,
                self.tbl_tasks.c.start_ts < end_ts,
            ))
        )
        word_map: dict[str, models.WordInfo] = {}
        for row in result:
            word_info = word_map.get(row.word)
            if word_info is None:
                word_info = word_map[row.word] = models.WordInfo(word=row.word)

            elapsed = (row.end_ts - row.start_ts).seconds
            word_info.total_count += 1
            word_info.total_elapsed += elapsed

        return word_map

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
