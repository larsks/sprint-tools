import github
import logging

from functools import cached_property

from moc_sprint_tools import defaults

LOG = logging.getLogger(__name__)
DEFAULT_ORG = 'CCI-MOC'
DEFAULT_BACKLOG = 'mocbacklog'


class ApplicationError(Exception):
    pass


class BoardNotFoundError(ApplicationError):
    pass


class Sprintman(github.Github):
    def __init__(self, token, org_name=None, backlog_name=None):
        super().__init__(token)
        self._org_name = org_name if org_name else DEFAULT_ORG
        self._backlog_name = backlog_name if backlog_name else DEFAULT_BACKLOG

    @cached_property
    def organization(self):
        return self.get_organization(self._org_name)

    @property
    def open_sprints(self):
        for board in self.organization.get_projects('open'):
            if board.name.lower().strip().startswith('sprint'):
                yield board

    def get_sprint(self, name):
        for board in self.open_sprints:
            if board.name.lower() == name.lower():
                return board
        raise BoardNotFoundError(name)

    @property
    def closed_sprints(self):
        for board in self.organization.get_projects('closed'):
            if board.name.lower().startswith('sprint'):
                yield board

    @property
    def backlog(self):
        for board in self.organization.get_projects('open'):
            if board.name.lower() == self._backlog_name.lower():
                break
        else:
            raise BoardNotFoundError(self._backlog_name)

        return board

    def get_column(self, board, name):
        for c in board.get_columns():
            if c.name.lower() == name.lower():
                return c

    def create_sprint(self, name):
        board = self.organization.create_project(name)
        board.edit(private=False)
        LOG.info('Created board %s' % board.name)

        for column in defaults.default_sprint_columns:
            board.create_column(column)

        return board
