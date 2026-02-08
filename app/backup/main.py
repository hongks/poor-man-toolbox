import click

from .config import Config
from .service import Backup


@click.command()
@click.option(
    "--type",
    "-p",
    help="run only selected type.",
)
@click.option(
    "--target",
    "-t",
    help="run only selected target.",
)
@click.option(
    "--list",
    "-l",
    is_flag=True,
    help="list available targets.",
)
@click.option(
    "--generate",
    "-g",
    is_flag=True,
    help="generate skeleton filesync.xml.",
)
@click.option(
    "--reset",
    "-e",
    is_flag=True,
    help="remove downloaded files and generated logs.",
)
@click.help_option(
    "--help",
    "-h",
    help="show this message and exit.",
)
@click.pass_context
def main(
    context: click.Context,
    type: str,
    target: str,
    list: bool,
    generate: bool,
    reset: bool,
):
    config = Config()
    config.load()

    backup = Backup(config, context)
    backup.run(type, target, list, generate, reset)


if __name__ == "__main__":
    main()
