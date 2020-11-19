## Jobs

These jobs run every half hour via a [github action][action].

[action]: .github/workflows/sprint-board-maintenance.yml

### label-cards-in-sprint.py

This script will iterate over cards on all sprint boards (boards that start
with the word "Sprint").

It will add the `accepted` label to all issues and pull requests that are
included on an open board.

It will remove the `accepted` label from all isues that are included in a
closed board and are not *also* included in one or more open boards.

### move-top-notes-to-top.py

Ensure that important notes stay on top: move notes that start with `[top]` to
the top of their respective column.

### label-needs-description.py

Find cards in the backlog that need a description and label them
`needs_description`. We can use this during backlog grooming to highlight cards
that might need additional information.
