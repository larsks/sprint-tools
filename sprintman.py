import github
import logging

from functools import wraps

LOG = logging.getLogger(__name__)


def cached(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        attr = f'_{func.__name__}'
        if hasattr(self, attr):
            return getattr(self, attr)

        res = func(self, *args, **kwargs)
        setattr(self, attr, res)
        return res

    return wrapped


class Sprintman(github.Github):
    def __init__(self, token, org):
        super().__init__(token)
        self._org_name = org

    @property
    @cached
    def organization(self):
        return self.get_organization(self._org_name)

    @property
    def open_sprints(self):
        for board in self.organization.get_projects('open'):
            if board.name.lower().startswith('sprint'):
                yield board

    @property
    def closed_sprints(self):
        for board in self.organization.get_projects('closed'):
            if board.name.lower().startswith('sprint'):
                yield board
