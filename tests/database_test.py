import datetime
import os
import shutil
import tempfile
from typing import Optional

import pytest
import sqlalchemy as sa
import sqlalchemy.engine.base

from wastedyears import database, models

_tmp_dir: Optional[str] = None
_test_engine: Optional[sqlalchemy.engine.base.Engine] = None


def open_test_db() -> database.WastedYearsDB:
    global _tmp_dir, _test_engine
    if _test_engine is None:
        _tmp_dir = tempfile.mkdtemp(prefix='wastedyears.database_test.')
        db_url = 'sqlite:///' + os.path.join(_tmp_dir, 'test.sqlite')
        _test_engine = database.create_engine(db_url)

    db = database.WastedYearsDB(_test_engine.connect())
    db.init_schema()
    return db


def teardown():
    global _tmp_dir
    if _tmp_dir is not None:
        shutil.rmtree(_tmp_dir)
        _tmp_dir = None


class TestWastedYearsDB:
    @pytest.fixture
    def db(self):
        db = open_test_db()
        yield db
        db.close()

    def test_add_task(self, db: database.WastedYearsDB):
        start_ts = parse_ts('2022-07-15T11:53:21')
        end_ts = parse_ts('2022-07-15T11:56:27')
        description = 'fiddle la-la device'

        task = models.Task(
            start_ts=start_ts,
            end_ts=end_ts,
            description=description)

        task_id = db.add_task(task)
        assert task_id == 1

        # assert that the task itself was written
        tasks = db.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].start_ts == start_ts
        assert tasks[0].end_ts == end_ts
        assert tasks[0].description == description

        # assert that the words in task.description were written
        assert self._get_words(db) == [
            ('device', 1, 186),
            ('fiddle', 1, 186),
            ('la', 1, 186),
        ]

        # and assert that the words were associated with the task
        task_words = self._get_task_words(db)
        assert task_words == [
            (task_id, 'device'),
            (task_id, 'fiddle'),
            (task_id, 'la'),
        ]

        # write another task with some new words in the description
        task = models.Task(
            start_ts=parse_ts('2022-07-15T11:57:01'),
            end_ts=parse_ts('2022-07-15T12:03:16'),
            description='fiddle /thing/ device!')
        task_id = db.add_task(task)
        assert task_id == 2

        assert self._get_words(db) == [
            ('device', 2, 186 + 375),
            ('fiddle', 2, 186 + 375),
            ('la', 1, 186),
            ('thing', 1, 375)
        ]

        task_words = self._get_task_words(db)
        assert task_words == [
            (1, 'device'),
            (1, 'fiddle'),
            (1, 'la'),
            (2, 'device'),
            (2, 'fiddle'),
            (2, 'thing'),
        ]

    def test_upsert_words(self, db: database.WastedYearsDB):
        ts = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        rows = [{'task_id': task_id} for task_id in [1, 2, 3, 4, 5]]
        db.conn.execute(
            db.tbl_tasks.insert()
            .values(
                task_id=None,
                update_ts=ts,
                start_ts=ts,
                end_ts=ts,
                description='',
            ),
            rows,
        )

        def get_words():
            tbl = db.tbl_words
            return db.conn.execute(
                sa.select([tbl.c.word, tbl.c.total_count, tbl.c.total_elapsed])
                .order_by(tbl.c.word)
            ).fetchall()

        new_words = db.upsert_words(1, [], 10)
        assert new_words == {}

        # all new words
        new_words = db.upsert_words(2, ['hello', 'd!ng/', 'bla9'], 5)
        assert new_words == {
            'hello': 1,
            'd!ng/': 2,
            'bla9': 3,
        }

        # make sure total_count, total_elapsed are set
        expect = [
            ('bla9', 1, 5),
            ('d!ng/', 1, 5),
            ('hello', 1, 5),
        ]
        assert get_words() == expect

        # all existing words
        new_words = db.upsert_words(3, ['hello', 'd!ng/', 'bla9'], 15)
        assert new_words == {}

        # make sure total_count, total_elapsed are updated
        expect = [
            ('bla9', 2, 20),
            ('d!ng/', 2, 20),
            ('hello', 2, 20),
        ]
        assert get_words() == expect

        # a mix of new and existing words
        new_words = db.upsert_words(4, ['hello', 'foo', 'bla8', 'bla9'], 5)
        assert new_words == {
            'foo': 4,
            'bla8': 5,
        }

        # make sure total_count, total_elapsed are set or updated
        expect = [
            ('bla8', 1, 5),
            ('bla9', 3, 25),
            ('d!ng/', 2, 20),
            ('foo', 1, 5),
            ('hello', 3, 25),
        ]
        assert get_words() == expect

    def _get_words(self, db: database.WastedYearsDB) -> list[str]:
        tbl = db.tbl_words
        rows = db.conn.execute(
            sa.select([tbl.c.word, tbl.c.total_count, tbl.c.total_elapsed])
            .order_by(tbl.c.word)
        ).fetchall()
        return rows

    def _get_task_words(self, db: database.WastedYearsDB) -> list[tuple[int, str]]:
        tbl_tw = db.tbl_task_words
        tbl_w = db.tbl_words
        join = (sa.select([tbl_tw.c.task_id, tbl_w.c.word])
                .select_from(tbl_tw.join(tbl_w))
                .order_by(tbl_tw.c.task_id, tbl_w.c.word))
        return db.conn.execute(join).fetchall()


def parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    return dt.replace(tzinfo=datetime.timezone.utc)
