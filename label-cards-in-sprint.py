import click
import github
import logging
import os

from sprintman import Sprintman

maybe_unlabel = {}


def process_closed_board(board):
    logging.info('processing closed board "%s"', board.name)
    for col in board.get_columns():
        logging.debug('processing column "%s"', col.name)
        for card in col.get_cards():
            content = card.get_content()
            if content is None:
                continue

            logging.debug('processing card "%s"', content.title)
            if content.state == 'open' and any(label.name == 'accepted' for label in content.labels):
                logging.info('found open card "%s" on closed board "%s"',
                             content.title, board.name)
                maybe_unlabel[content.url] = content


def process_open_board(board):
    logging.info('processing open board "%s"', board.name)
    for col in board.get_columns():
        logging.debug('processing column "%s"', col.name)
        for card in col.get_cards():
            content = card.get_content()
            if content is None:
                continue

            logging.debug('processing card "%s"', content.title)
            if any(label.name == 'accepted' for label in content.labels):
                logging.debug('card "%s" is already accepted', content.title)
            else:
                logging.info('adding "accepted" label to card "%s"', content.title)
                content.add_to_labels('accepted')

            if content.url in maybe_unlabel:
                logging.info('found card "%s" on open board "%s"',
                             card.name, board.name)
                del maybe_unlabel[content.url]


@click.command()
@click.option('--verbose', '-v', type=int, count=True)
@click.option('--organization', '-o', required=True)
def main(verbose, organization):
    try:
        loglevel = ['WARNING', 'INFO', 'DEBUG'][verbose]
    except IndexError:
        loglevel = 'DEBUG'

    logging.basicConfig(level=loglevel)

    try:
        sm = Sprintman(os.environ.get('GH_API_TOKEN'), organization)

        for board in sm.closed_sprints:
            process_closed_board(board)

        for board in sm.open_sprints:
            process_open_board(board)

        for url, content in maybe_unlabel.items():
            logging.info('removing "accepted" label from card "%s"', content.title)
            content.remove_from_labels('accepted')
    except github.GithubException as err:
        raise click.ClickException(err)


if __name__ == '__main__':
    main()
