"""
My own clean up script!
"""

import logging
import pathlib
import shutil

import click

from modules import files
from modules import folders
from modules import movies as m_movies


@click.group()
@click.option(
    "-d", "--debug", is_flag=True, default=False, help="Display debug messages."
)
@click.option(
    "-l", "--list-only", is_flag=True, default=False, help="Dry-run, as in do nothing."
)
@click.help_option("-h", "--help")
@click.version_option(version="1.0.0")
@click.pass_context
def main(ctx, debug, list_only):
    """This is a cleanup script I written to ease my life."""

    # main will only execute if options and/or commands are pass through the
    # prompt
    ctx.obj = {"debug": debug, "list_only": list_only}

    if debug:
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
        click.echo("Debug mode is on.")

    if list_only:
        click.echo("List mode is on.\n")
    else:
        click.echo("")


@main.command("files")
@click.option(
    "-m",
    "--move",
    is_flag=True,
    default=False,
    help="Move file from point A to B for given extension.",
)
@click.help_option("-h", "--help")
@click.argument("source", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument("destination", type=click.STRING)
@click.pass_context
def files(ctx, move, source, destination):
    """Perform actions on files."""

    list_only = ctx.obj["list_only"]

    if move:
        move_files(list_only, source, destination)
    else:
        print(ctx.get_help())


@main.command("folders")
@click.option(
    "-r",
    "--remove",
    type=click.Choice(["dupe", "empty"]),
    help="Remove dupe(DupeGuru) duplicate files or empty folders.",
)
@click.option(
    "-p",
    "--parent",
    is_flag=True,
    default=False,
    help="Remove the parent folder, use together with -r, --remove.",
)
@click.option(
    "-t", "--tree", type=click.STRING, help="Traverse folders for given extension."
)
@click.help_option("-h", "--help")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.pass_context
def folders(ctx, remove, parent, tree, path):
    """Perform actions on folders for given extension."""
    # might want to use 'def folders(**kwargs):'
    # to read the value use 'kwargs['ctx']'

    list_only = ctx.obj["list_only"]

    if remove == "dupe":
        remove_dupeguru_duplicate_files(list_only, path)
    elif remove == "empty":
        remove_empty_folders(list_only, path, parent)
    elif tree:
        tree_folders(path, tree)
    else:
        print(ctx.get_help())


@main.command("movies")
@click.option(
    "-q", "--query", type=click.STRING, help="Search IMDB based on the filename given."
)
@click.option(
    "-s",
    "--search",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Search IMDB based on the folder given.",
)
@click.help_option("-h", "--help")
@click.pass_context
def movies(ctx, query, search):
    """Everything start here..."""

    list_only = ctx.obj["list_only"]

    if query:
        m_movies.search(query)
    elif search:
        items = folders.tree(search, ".mkv")
        i = 0

        for item in items:
            i += 1
            click.echo("\n >> ({:3d})".format(i))

            path = pathlib.Path(item)
            filepath = m_movies.search(path.name)

            if not list_only and filepath != "":
                filepath = "." + filepath
                fpath = pathlib.Path(filepath)

                if not fpath.parent.exists():
                    fpath.parent.mkdir()
                if not fpath.exists():
                    shutil.move(item, filepath)
                else:
                    click.echo("\n @ File exist! Unable to move!")
    else:
        print(ctx.get_help())


# pylint: disable=no-value-for-parameter
if __name__ == "__main__":
    main()
