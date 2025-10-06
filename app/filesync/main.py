import click

from .config import Config
from .service import FileSync


@click.command()
@click.option(
    "--download",
    "-w",
    is_flag=True,
    help="download files from remote server.",
)
@click.option(
    "--check",
    "-c",
    is_flag=True,
    help="check files downloaded from remote server.",
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
    download: bool,
    check: bool,
    target: str,
    list: bool,
    generate: bool,
    reset: bool,
):
    config = Config()
    config.load()

    filesync = FileSync(config, context)
    filesync.run(download, check, target, list, generate, reset)


if __name__ == "__main__":
    main()
