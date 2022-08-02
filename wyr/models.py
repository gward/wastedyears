import dataclasses
import datetime
import re
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


@dataclasses.dataclass
class WordInfo:
    word_id: int = 0
    word: str = ''
    total_count: int = 0
    total_elapsed: int = 0

    def __str__(self):
        return f'{self.total_count:-6}{self.total_elapsed:-8}s  {self.word}'


_simple_url_re = re.compile(r'[a-z0-9\+\-]+://\S+')
_split_re = re.compile(r'\b')


def split_description(desc: str) -> list[str]:
    urls = []

    def repl(match):
        urls.append(match.group())
        return ''

    desc = _simple_url_re.sub(repl, desc)
    words = []
    for (idx, chunk) in enumerate(_split_re.split(desc)):
        if idx % 2 == 1:
            words.append(chunk)

    return sorted(words) + urls
