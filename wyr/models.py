import dataclasses
import datetime
from typing import Optional


@dataclasses.dataclass
class Task:
    '''a single task, i.e. a span of time with one activity'''

    task_id: Optional[int] = None
    update_ts: Optional[datetime.datetime] = None
    start_ts: Optional[datetime.datetime] = None
    end_ts: Optional[datetime.datetime] = None
    description: str = ''

    def __str__(self):
        return f'{self.start_ts} … {self.end_ts}: {self.description}'
