import click
import datetime
import github
import jinja2
import json
import logging

from moc_sprint_tools.sprintman import BoardNotFoundError
from moc_sprint_tools import defaults

LOG = logging.getLogger(__name__)


def Date(val):
    '''transform date on the command line into a datetime.date object

    the values 'now' and 'today' both evaluate to the current day
    (datetime.date.today()).
    '''

    if val in ['now', 'today']:
        date = datetime.date.today()
    else:
        date = datetime.date.fromisoformat(val)

    if date is None:
        raise ValueError(val)

    return date


def find_notes_issue(repo, title):
    '''find an issue by title in the specified repository'''

    for issue in repo.get_issues(state='open'):
        if issue.title == title:
            return issue


def dump_date_as_iso8601(val):
    '''used to serialize datetime.date objects to JSON'''

    if isinstance(val, datetime.date):
        return val.isoformat()
    else:
        return val


def check_overlaps(api, date):
    '''look for existing sprints that conflict with the current date

    since this function has to iterate through all existing sprint boards,
    it also calculates the immediately prior sprint.

    returns a (previous_board, list_of_conflicts) tuple to the caller.
    '''

    conflicts = []
    sprints = []

    for sprint in api.open_sprints:
        try:
            md = json.loads(sprint.body)
        except (TypeError, json.decoder.JSONDecodeError):
            continue

        for attr in ['week1', 'week2']:
            md[attr] = datetime.date.fromisoformat(md[attr])

        sprints.append((md['week1'], md['week2'], sprint))

        if md['week1'] < date < md['week2']:
            conflicts.append(sprint)

    try:
        prev_week1, prev_week2, prev_board = sorted(sprints)[-1]
        if prev_week1 >= date:
            prev_board = None
    except IndexError:
        prev_board = None

    return prev_board, conflicts


@click.command(name='create-sprint-boards')
@click.option('--copy-cards/--no-copy-cards', default=True)
@click.option('--date', '-d', type=Date, default='now')
@click.option('--templates', '-t')
@click.option('--notes-repo', '-n', default=defaults.default_sprint_notes_repo)
@click.option('--force', '-f', is_flag=True)
@click.option('--check-only', '-n', is_flag=True)
@click.pass_context
def main(ctx, date, templates, notes_repo, copy_cards, force, check_only):
    '''create sprint board for the current date

    create a new project board for a sprint beginning on the current date (or
    on the argument to --date, if provided). create-sprint-board will not
    create a sprint board if one with the same name already exists. It will not
    create a sprint board if the dates overlap with an existing open sprint
    unless you provide the --force option.
    '''

    api = ctx.obj

    loaders = []
    if templates:
        loaders.append(jinja2.FileSystemLoader(templates))
    loaders.append(jinja2.PackageLoader('moc_sprint_tools'))

    env = jinja2.Environment(
        loader=jinja2.ChoiceLoader(loaders),
    )
    env.globals['api'] = api

    try:
        week1 = date
        week2 = date + datetime.timedelta(days=14)

        sprint_title = env.get_template('sprint_title.j2').render(
            week1=week1, week2=week2
        )

        sprint_description = json.dumps(dict(
            week1=week1,
            week2=week2
        ), default=dump_date_as_iso8601)

        sprint_notes_title = env.get_template('sprint_notes_title.j2').render(
            week1=week1, week2=week2
        )

        sprint_notes_description = env.get_template('sprint_notes_description.j2').render(
            week1=week1, week2=week2
        )

        repo = api.organization.get_repo(notes_repo)

        # check if board exists

        try:
            api.get_sprint(sprint_title)
            LOG.warning('sprint board "%s" already exists.' % sprint_title)
            return
        except BoardNotFoundError:
            LOG.info('preparing to create sprint board "%s"' % sprint_title)

        #  check for existing notes issue
        issue = find_notes_issue(repo, sprint_notes_title)
        if issue:
            LOG.info('using existing notes issue %s#%s',
                     issue.repository.full_name, issue.number)

        # check for overlap with existing sprint

        previous, conflicts = check_overlaps(api, week1)
        LOG.debug('found previous board: %s', previous)
        LOG.debug('found conflicts: %s', conflicts)
        if conflicts and not force:
            titles = ', '.join(sprint.name for sprint in conflicts)
            raise click.ClickException(
                f'new sprint {sprint_title} overlaps with {titles}')

        if previous:
            LOG.info('found previous sprint %s', previous.name)

        if check_only:
            return

        ##
        ## create resources after this point
        ##

        # create project board

        LOG.info('creating board %s', sprint_title)
        board = api.create_sprint(sprint_title, body=sprint_description)

        # create sprint notes issue

        if not issue:
            LOG.info('creating sprint notes issue in %s', notes_repo)
            issue = repo.create_issue(title=sprint_notes_title,
                                      body=sprint_notes_description)

        # add sprint note to card in notes column

        LOG.info('creating sprint notes card')
        notes = api.get_column(board, 'notes')
        notes.create_card(
            content_id=issue.id,
            content_type='Issue',
        )

        # copy cards if requested
        if copy_cards and previous:
            LOG.info('copying cards from {previous.name}')
            api.copy_board(previous, board)
        elif copy_cards:
            LOG.warning('not copying cards (no previous board)')

    except github.GithubException as err:
        raise click.ClickException(err)
