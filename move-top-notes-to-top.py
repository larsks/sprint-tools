import click
import github
import logging
import os

from itertools import chain

from sprintman import Sprintman

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

        for board in chain(sm.open_sprints, [sm.backlog]):
            for col in board.get_columns():
                for card in col.get_cards():
                    if not card.note:
                        continue

                    if card.note.startswith('[top]'):
                        logging.info('moving note in board %s, column %s',
                                     board, col)
                        card.move('top', col)

    except github.GithubException as err:
        raise click.ClickException(err)


if __name__ == '__main__':
    main()
