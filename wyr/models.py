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
