'''read tasks from a text file

expected file format:

<date>
----------
<start_ts> ".." <end_ts> <task_description>
<start_ts> ".." <end_ts> <task_description>
[...]

where:

  <date>      : yyyy-mm-dd
  <start_ts>  : hh:mm
  <end_ts>    : hh:mm
  <task_description> : anything

Leading and trailing whitespace is stripped. Blank lines are ignored.
All dates/times must be in the local timezone.

Then repeat that block for as many dates as you please.
'''

import datetime
import re
from typing import Optional

from . import models, database

date_re = re.compile(r'^(\d{4})-(\d{2})-(\d{2})$')
divider_re = re.compile(r'^-+$')
task_re = re.compile(r'^(\d{2}):(\d{2})\s*\.\.\s*(\d{2}):(\d{2})\s+(.*)')


def ingest(db: database.WastedYearsDB, infile):
    current_date = None
    previous_task = None
    for (line_num, line) in enumerate(infile):
        line = line.strip()
        if line == '':
            continue
        elif match := date_re.match(line):
            (year, month, day) = (int(val) for val in match.groups())
            current_date = datetime.datetime(year, month, day)
        elif divider_re.match(line):
            continue
        elif match := task_re.match(line):
            if current_date is None:
                raise ValueError(
                    f'{infile.name}:{line_num+1}: task without any date')

            task = _parse_task(current_date, previous_task, match)
            print(task)
            previous_task = task
        else:
            raise ValueError(
                f'{infile.name}{line_num+1}: could not parse line')


def _parse_task(
        current_date: datetime.datetime,
        previous_task: Optional[models.Task],
        match: re.Match):
    (start_hour, start_min, end_hour, end_min) = match.group(1, 2, 3, 4)
    desc = match.group(5)
    start_ts = current_date.replace(
        hour=int(start_hour), minute=int(start_min))
    end_ts = current_date.replace(
        hour=int(end_hour), minute=int(end_min))

    # convert to UTC
    start_ts = start_ts.astimezone(datetime.timezone.utc)
    end_ts = end_ts.astimezone(datetime.timezone.utc)

    # if a task says "10:00 .. 10:00", it could be 1 s .. 59 s: pick 30 s
    if start_ts == end_ts:
        end_ts = end_ts.replace(second=30)

    # if previous task had a tweaked end_ts, account for that
    if (previous_task is not None and
            previous_task.end_ts is not None and
            start_ts < previous_task.end_ts):
        start_ts = previous_task.end_ts

    task = models.Task(
        start_ts=start_ts,
        end_ts=end_ts,
        description=desc)
    return task
