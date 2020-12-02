import click
import github
import logging
import os

from moc_sprint_tools.sprintman import Sprintman

maybe_unlabel = {}


@click.command()
@click.option('--verbose', '-v', type=int, count=True)
@click.option('--organization', '-o')
def main(verbose, organization):
    try:
        loglevel = ['WARNING', 'INFO', 'DEBUG'][verbose]
    except IndexError:
        loglevel = 'DEBUG'

    logging.basicConfig(level=loglevel)

    try:
        sm = Sprintman(os.environ.get('GH_API_TOKEN'),
                       org_name=organization)

        for col in sm.backlog.get_columns():
            for card in col.get_cards():
                content = card.get_content()
                if not content:
                    continue

                if not content.body and not any(label.name == 'needs_description' for label in content.labels):
                    logging.info('card "%s" has no description',
                                 content.title)
                    content.add_to_labels('needs_description')
                elif content.body and any(label.name == 'needs_description' for label in content.labels):
                    logging.info('card "%s" has added a description',
                                 content.title)
                    content.remove_from_labels('needs_description')

    except github.GithubException as err:
        raise click.ClickException(err)


if __name__ == '__main__':
    main()
