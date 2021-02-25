import click
import datetime
import github
import jinja2
import json
import logging

from moc_sprint_tools.sprintman import BoardNotFoundError

LOG = logging.getLogger(__name__)


def Date(val):
    if val in ['now', 'today']:
        date = datetime.date.today()
    else:
        date = datetime.date.fromisoformat(val)

    if date is None:
        raise ValueError(val)

    return date


def dump_date_as_iso8601(val):
    if isinstance(val, datetime.date):
        return val.isoformat()
    else:
        return val


def check_overlaps(api, date):
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

        if md['week1'] < date < md['week2'] + datetime.timedelta(days=7):
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
@click.option('--force', '-f', is_flag=True)
@click.option('--check-only', '-n', is_flag=True)
@click.pass_context
def main(ctx, date, templates, copy_cards, force, check_only):
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
        week2 = date + datetime.timedelta(days=7)

        sprint_title = env.get_template('sprint_title.j2').render(
            week1=week1, week2=week2
        )

        sprint_description = json.dumps(dict(
            week1=week1,
            week2=week2
        ), default=dump_date_as_iso8601)

        # check if board exists

        try:
            api.get_sprint(sprint_title)
            LOG.warning('sprint board "%s" already exists.' % sprint_title)
            return
        except BoardNotFoundError:
            LOG.info('preparing to create sprint board "%s"' % sprint_title)

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

        # copy cards if requested
        if copy_cards and previous:
            LOG.info('copying cards from %s', previous.name)
            api.copy_board(previous, board)
        elif copy_cards:
            LOG.warning('not copying cards (no previous board)')

    except github.GithubException as err:
        raise click.ClickException(err)
