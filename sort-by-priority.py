import click
import github
import jinja2
import logging
import os
import re

from itertools import chain

from sprintman import Sprintman

LOG = logging.getLogger(__name__)

re_priority = re.compile(r'(\[\s*(?P<prio>\d+)\s*\]\s*)?(?P<title>.*)')
title_format = jinja2.Template('{% if priority is not none %}[{{ priority }}] {% endif %}{{ title }}')


class CardWrapper:
    def __init__(self, card):
        self.card = card

    def __getattr__(self, k):
        return getattr(self.card, k)

    def __repr__(self):
        title = self.title.splitlines()[0][:40].strip()
        return f'<title="{title!r}" priority={self.priority} id={self.id}>'

    def __lt__(self, other):
        if self.priority is None:
            return False
        elif other.priority is None:
            return True
        else:
            return self.priority < other.priority

    @property
    def _raw_title(self):
        if self.note:
            title = self.note.splitlines()[0]
        else:
            content = self.get_content()
            title = content.title

        return title

    @_raw_title.setter
    def _raw_title(self, title):
        if self.note:
            lines = self.note.splitlines()
            lines[0] = title
            note = '\n'.join(lines)
            self.edit(note=note)
        else:
            content = self.get_content()
            content.edit(title=title)

    @property
    def title(self):
        mo = re_priority.match(self._raw_title)
        return mo.group('title')

    @title.setter
    def title(self, title):
        self.set_title_and_priority(self.priority, title)

    @property
    def priority(self):
        mo = re_priority.match(self._raw_title)
        prio = mo.group('prio')
        return int(prio) if prio is not None and prio.isdigit() else None

    @priority.setter
    def priority(self, priority):
        self.set_priority_and_title(self, priority, self.title)

    def set_priority_and_title(self, priority, title):
        self._raw_title = title_format.render(
            title=title,
            priority=priority,
        )


@click.command()
@click.option('--board', '-b', 'selected_boards', multiple=True, default=[])
@click.option('--verbose', '-v', type=int, count=True)
@click.option('--organization', '-o')
def main(selected_boards, verbose, organization):
    try:
        loglevel = ['WARNING', 'INFO', 'DEBUG'][verbose]
    except IndexError:
        loglevel = 'DEBUG'

    logging.basicConfig(level=loglevel)

    try:
        sm = Sprintman(os.environ.get('GH_API_TOKEN'),
                       org_name=organization)

        for board in chain(sm.open_sprints, [sm.backlog]):
            if selected_boards and board.name not in selected_boards:
                continue

            LOG.info('procssing board %s', board.name)
            for col in board.get_columns():
                LOG.info('processing column %s', col.name)
                cards = sorted(CardWrapper(card) for card in col.get_cards())
                prev = None
                for card in cards:
                    if card.priority is None:
                        break
                    if prev is None:
                        LOG.info('move %r to top', card.title)
                        card.move('top', col)
                    else:
                        LOG.info('move %r after %r', card.title, prev.title)
                        card.move(f'after:{prev.id}', col)

                    prev = card

    except github.GithubException as err:
        raise click.ClickException(err)


if __name__ == '__main__':
    main()
