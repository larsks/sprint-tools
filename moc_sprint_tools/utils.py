import click
import code
import fnmatch


@click.command()
@click.pass_context
def shell(ctx):
    api = ctx.obj
    print('Access GitHub using the "api" variable')
    code.interact(local=locals())


@click.command()
@click.argument('patterns', nargs=-1)
@click.pass_context
def repos(ctx, patterns):
    api = ctx.obj
    repos = (
        repo for repo in api.organization.get_repos()
        if not patterns
        or any(fnmatch.fnmatch(repo.name, pattern) for pattern in patterns)
    )
    print('\n'.join(repo.name for repo in repos))


