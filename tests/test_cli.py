import click.testing
import datetime
import pytest

from unittest import mock

import moc_sprint_tools.cli
import moc_sprint_tools.sprintman


@pytest.fixture
def api(api_class, org):
    mock_api_object = mock.Mock()
    mock_api_object.organization = org
    api_class.return_value = mock_api_object

    yield mock_api_object


@pytest.fixture
def runner():
    return click.testing.CliRunner()


def test_main_no_args(api_class, runner):
    res = runner.invoke(moc_sprint_tools.cli.main, 'shell')
    assert res.exit_code == 0


def test_main_invalid_args(runner):
    res = runner.invoke(moc_sprint_tools.cli.main, 'invalid')
    assert res.exit_code == 2


def test_main_override_org(api_class, runner):
    res = runner.invoke(moc_sprint_tools.cli.main, '-o fake_org shell')
    assert res.exit_code == 0
    assert api_class.call_args[1]['org_name'] == 'fake_org'


def test_boards(api, runner, projects):
    res = runner.invoke(moc_sprint_tools.cli.main, 'boards')
    assert res.exit_code == 0
    assert res.stdout == '\n'.join(project.name for project in projects) + '\n'


def test_create_sprint_boards_no_copy(api, org, runner, projects):
    today = datetime.datetime.now()
    today.replace(hour=0, minute=0, second=0)
    api.get_sprint.side_effect = moc_sprint_tools.sprintman.BoardNotFoundError

    with mock.patch('moc_sprint_tools.cmd.create_sprint_boards.load_sprint_data') as load_sprint_data:
        load_sprint_data.return_value = [
            ('Test Sprint', today)
        ]

        res = runner.invoke(moc_sprint_tools.cli.main, 'create-sprint-boards', '--no-copy-cards')
        assert res.exit_code == 0
        assert api.create_sprint.call_args_list[0][0] == ('Test Sprint',)


def test_create_sprint_boards_duplicate_no_copy(caplog, api, org, runner, projects):
    today = datetime.datetime.now()
    today.replace(hour=0, minute=0, second=0)
    api.get_sprint.return_value = projects[0]

    with mock.patch('moc_sprint_tools.cmd.create_sprint_boards.load_sprint_data') as load_sprint_data:
        load_sprint_data.return_value = [
            (projects[0].name, today)
        ]

        res = runner.invoke(moc_sprint_tools.cli.main, 'create-sprint-boards', '--no-copy-cards')
        assert res.exit_code == 0
        assert not api.create_sprint.call_args_list


@pytest.mark.skip(reason='create-sprint-boards needs work')
def test_create_sprint_boards_copy(api, org, runner, projects):
    today = datetime.datetime.now()
    today.replace(hour=0, minute=0, second=0)
    api.get_sprint.side_effect = moc_sprint_tools.sprintman.BoardNotFoundError

    with mock.patch('moc_sprint_tools.cmd.create_sprint_boards.load_sprint_data') as load_sprint_data:
        load_sprint_data.return_value = [
            ('Test Sprint 1', today - datetime.timedelta(weeks=1)),
            ('Test Sprint 2', today)
        ]

        res = runner.invoke(moc_sprint_tools.cli.main, 'create-sprint-boards')
        assert res.exit_code == 0
        assert api.create_sprint.call_args_list[0][0] == ('Test Sprint 2',)
