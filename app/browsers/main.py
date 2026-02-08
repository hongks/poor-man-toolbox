import click

from .config import Config
from .service import Browser


@click.command()
@click.option(
    "--humblebundle",
    "-hb",
    is_flag=True,
    help="download ebooks (pdf, epub, cbz, mobi) purchased from humble bundle.",
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
@click.help_option(
    "--help",
    "-h",
    help="show this message and exit.",
)
@click.pass_context
def main(context: click.Context, humblebundle: bool, target: str, list: bool):
    config = Config()
    # config.load()

    folder = Browser(config, context)
    folder.run(humblebundle, target, list)


# ################################################################################
# where it all begins


if __name__ == "__main__":
    main()
