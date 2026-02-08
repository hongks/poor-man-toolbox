import click

from .config import Config
from .service import Folders


@click.command()
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
@click.help_option(
    "--help",
    "-h",
    help="show this message and exit.",
)
@click.pass_context
def main(context: click.Context, target: str, list: bool):
    config = Config()
    # config.load()

    folder = Folders(config, context)
    folder.run(target, list)


# ################################################################################
# where it all begins


if __name__ == "__main__":
    main()
