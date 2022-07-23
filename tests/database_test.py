import datetime
import os
import shutil
import tempfile

import pytest
import sqlalchemy as sa

from wyr import database, models

_tmp_dir = None
_test_engine = None


def open_test_db() -> database.WastedYearsDB:
    global _tmp_dir, _test_engine
    if _test_engine is None:
        _tmp_dir = tempfile.mkdtemp(prefix='wyr.database_test.')
        db_url = 'sqlite:///' + os.path.join(_tmp_dir, 'test.sqlite')
        _test_engine = database.create_engine(db_url)

    db = database.WastedYearsDB(_test_engine)
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
        description = 'fiddle whoop-de-la-la device'

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
        words = self._get_words(db)
        assert words == ['de', 'device', 'fiddle', 'la', 'whoop']

        # and assert that the words were associated with the task
        task_words = self._get_task_words(db)
        assert len(task_words) == 5
        assert task_words == [
            (task_id, 'de'),
            (task_id, 'device'),
            (task_id, 'fiddle'),
            (task_id, 'la'),
            (task_id, 'whoop'),
        ]

        # write another task with some new words in the description
        task = models.Task(
            start_ts=parse_ts('2022-07-15T11:57:01'),
            end_ts=parse_ts('2022-07-15T12:03:16'),
            description='fiddle /thing/ device!')
        task_id = db.add_task(task)
        assert task_id == 2

        words = self._get_words(db)
        assert words == ['de', 'device', 'fiddle', 'la', 'thing', 'whoop']

        task_words = self._get_task_words(db)
        assert task_words == [
            (1, 'de'),
            (1, 'device'),
            (1, 'fiddle'),
            (1, 'la'),
            (1, 'whoop'),
            (2, 'device'),
            (2, 'fiddle'),
            (2, 'thing'),
        ]

    def test_upsert_words(self, db: database.WastedYearsDB):
        new_words = db.upsert_words([])
        assert new_words == {}

        # all new words
        new_words = db.upsert_words(['hello', 'd!ng/', 'bla9'])
        assert new_words == {
            'hello': 1,
            'd!ng/': 2,
            'bla9': 3,
        }

        # all existing words
        new_words = db.upsert_words(['hello', 'd!ng/', 'bla9'])
        assert new_words == {}

        # a mix of new and existing words
        new_words = db.upsert_words(['hello', 'foo', 'bla8', 'bla9'])
        assert new_words == {
            'foo': 4,
            'bla8': 5,
        }

    def _get_words(self, db: database.WastedYearsDB) -> list[str]:
        tbl = db.tbl_words
        rows = db.conn.execute(
            sa.select(tbl.c.word).order_by(tbl.c.word))
        return [row[0] for row in rows]

    def _get_task_words(self, db: database.WastedYearsDB) -> list[tuple[int, str]]:
        tbl_tw = db.tbl_task_words
        tbl_w = db.tbl_words
        join = (sa.select(tbl_tw.c.task_id, tbl_w.c.word)
                .select_from(tbl_tw.join(tbl_w))
                .order_by(tbl_tw.c.task_id, tbl_w.c.word))
        return db.conn.execute(join).fetchall()


def parse_ts(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts)
    return dt.replace(tzinfo=datetime.timezone.utc)
