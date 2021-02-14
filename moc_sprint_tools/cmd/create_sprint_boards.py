import click
import datetime
import github
import jinja2
import logging

from moc_sprint_tools.sprintman import BoardNotFoundError
from moc_sprint_tools import defaults

LOG = logging.getLogger(__name__)

CARD_COPYING_MAP = {
    'notes': 'notes',
    'sprint backlog': 'sprint backlog',
    'in progress': 'in progress'
}


def Date(val):
    if val == 'now':
        date = datetime.datetime.now()
    else:
        date = datetime.datetime.strptime(val, '%Y-%m-%d')

    if date is None:
        raise ValueError(val)

    return date


@click.command(name='create-sprint-boards')
@click.option('--copy-cards/--no-copy-cards', default=True)
@click.option('--date', '-d', type=Date, default='now')
@click.option('--templates', '-t')
@click.pass_context
def main(ctx, date, templates, copy_cards):
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

        sprint_description = env.get_template('sprint_description.j2').render(
            week1=week1, week2=week2
        )

        try:
            api.get_sprint(sprint_title)
            LOG.warning('Sprint board "%s" already exists.' % sprint_title)
            return
        except BoardNotFoundError:
            pass

        # create project board

        LOG.info('creating board %s', sprint_title)
        board = api.create_sprint(sprint_title, body=sprint_description)

    except github.GithubException as err:
        raise click.ClickException(err)
