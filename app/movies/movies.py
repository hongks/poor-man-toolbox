"""movies.py, mostly routines related to imdb."""

import pathlib
import shutil

import click
import imdb


def compare_title(title, year, target):
    """Compare filename's title against IMDB's."""

    # try match first movie title against query
    mappings = {"and": {"&"}, "": {"[", "]", "(", ")", ":", ",", ".", "-", "\\"}}

    rtitle = target["title"]
    for key, values in mappings.items():
        for value in values:
            rtitle = rtitle.replace(value, key)

    if not (
        title.lower() == rtitle.lower()
        and year == target["year"]
        and "movie" in target["kind"]
    ):
        return False

    return True


def is_adult(genres, certificates):
    """Check whether the movie has adult rating."""

    found = False

    # quick check
    if "Adult" in genres:
        found = True
        return found

    # if all else fail, check certificates. not accurate.
    mappings = {"United States": {"NC-17"}, "Japan": {"R18+"}}

    # other certificates:
    #
    # "Argentina": {"+18"},
    # "Australia": {"R", "X"},
    # "Brazil": {"18"},
    # "Chile": {"18"},
    # "Finland": {"K-18"},
    # "France": {"18", "X"},
    # "Germany": {"18"},
    # "Hong Kong": {"III"},
    # "Iceland": {"18"},
    # "Ireland": {"18"},
    # "Italy": {"VM18"},
    # "Mexico": {"C", "D"},
    # "Norway": {"18"},
    # "New Zealand": {"R18"},
    # "Philippines": {"R-18", "X"},
    # "Portugal": {"M/18"},
    # "Romania": {"I.M.-18", "XXX"},
    # "Singapore": {"M18", "R(A)", "R21"},
    # "South Korea": {"18", "R"},
    # "Spain": {"18", "18/fig", "X"},
    # "Switzerland": {"18"},
    # "Taiwan": {"18+"},
    # "Thailand": {"18", "20"},
    # "Turkey": {"18+"},
    # "United Arab Emirates": {"18+"},
    # "United Kingdom": {"18", "R18"},
    # "Ukraine": {"18"},
    # "Venezuela": {"D"},
    # "Vietnam": {"C18"},

    for certificate in certificates:
        if certificate.find("::") > -1:
            continue

        country, rating = certificate.split(":")
        for key, values in mappings.items():
            if country == key and rating in values:
                found = True

    return found


def move(source, target):
    """Move the files based on the IMDB search result to here."""

    path = pathlib.Path(source)
    for idx, file in enumerate(path.rglob("*.*")):
        if not file.is_file():
            continue
        if file.suffix not in [".mkv", ".mp4"]:
            continue

        click.echo("\n >> ({:3d})".format(idx))
        filepath = search(file.name)

        if filepath == "":
            continue

        fpath = pathlib.Path("{}{}".format(target, filepath))
        if not fpath.parent.exists():
            fpath.parent.mkdir(parents=True, exist_ok=True)

        if not fpath.exists():
            if file != fpath:
                shutil.move(file, fpath)
            else:
                click.echo("\n @ No action required!")
        else:
            click.echo("\n @ File exist! Unable to move!")


def new_path(target):
    """Build new target path."""

    filepath = ""
    for key in {"Family", "Musical", "Animation"}:
        if key in target["genres"]:
            filepath = filepath + "/" + key
            break

    if not filepath:
        filepath = "/" + target["genres"][0]

    mappings = {
        "Chinese": {"cmn", "nan", "yue", "zn"},
        "English": {"en"},
        "French": {"fr"},
        "German": {"de"},
        "Italian": {"it"},
        "Japanese": {"ja"},
        "Korean": {"ko"},
        "Mongolian": {"mn"},
        "Russian": {"ru"},
    }

    if target["language codes"]:
        for key, values in mappings.items():
            if target["language codes"][0] in values:
                filepath += "/{}".format(key)
                break

    return filepath


def parse_filename(text):
    """Parse and clean up the TEXT before searching."""

    # always start with lowercase
    text = text.lower()

    # cleaning in general in sequence
    mappings = {"": {"[", "]", "(", ")", ","}}

    for key, values in mappings.items():
        for value in values:
            text = text.replace(value, key)

    while ".." in text:
        text = text.replace("..", ".")

    # get prefix, suffix
    words = text.split(".")
    prefix = ""
    year = 1900
    suffix = ""

    for word in words:
        if word.isnumeric() and int(word) > year:
            year = int(word)
            break
        prefix += "{}.".format(word)

    prefix = prefix[:-1].title()
    suffix = text[len(prefix) + len(str(year)) + 1 :]

    # cleaning, suffix only, in sequence
    mappings = {
        ".720p.": {".720p."},
        ".BluRay.": {".bluray."},
        ".AAC.": {".aac."},
        ".Ganool.": {".ganool.", ".ganol."},
        ".": {
            " ",
            ".ag.",
            ".com.",
            ".cx.",
            ".is.",
            ".li.",
            ".movie.",
            ".online.",
            ".ph.",
            ".video.",
        },
        ".mkv": {".mp4", ".mkv"},
    }

    new_suffix = ""
    for key, values in mappings.items():
        for value in values:
            suffix = suffix.replace(value, key)
            new_suffix += value

    suffix = new_suffix
    text = "{}.{}{}".format(prefix, year, suffix)
    return {
        "text": text,
        "prefix": prefix,
        "year": year,
        "suffix": suffix,
        "title": prefix.replace(".", " "),
    }


def recover(logfile):
    """Recover missing year, based on movies.search function."""

    filename = ""
    year = ""
    filepath = ""

    with open(logfile, "r") as file:
        for line in file:
            line = line.rstrip("\r\n")
            line = line.rstrip("\n")

            if line.startswith(" >> Filename: "):
                filename = line[14:]
                year = ""
                filepath = ""
                continue

            if line.startswith("  ! Title: "):
                idx = line.find("Year: ") + 6
                year = line[idx : idx + 4]
                continue

            if line.startswith("  @ /"):
                filepath = line[4:]
            if filename and year and filepath:
                idx = line.rfind("/")
                new_filepath = "{}/{}".format(filepath[: idx - 4], filename)
                print("mv {} {}".format(filepath[1:], new_filepath[1:]))

                filename = ""
                year = ""
                filepath = ""


def search(filename):
    """Search IMDB."""

    # parse the filename
    query = parse_filename(filename)

    # get imdb result
    handler = imdb.IMDb()
    results = handler.search_movie("{} {}".format(query["title"], query["year"]))
    click.echo(" >> Filename: {}".format(filename))
    click.echo(
        "  ! Title: {}, Year: {}, Found: {} result(s).".format(
            query["title"], query["year"], len(results)
        )
    )

    # TODO: also loop until year is found
    # /mnt/Seagate/Movies/Action/English/Ghostbusters.1984.remastered.BluRay.720p.Ganool.mkv

    # loop until first movie found
    found = ""
    for result in results:
        if result["kind"] == "movie":
            found = result
            handler.update(found)
            break

    filepath = ""
    if not found:
        click.echo("  ! No matching result found. Quiting.")
        return filepath

    # check whether title is same or not
    if not compare_title(query["title"], query["year"], found):
        click.echo("  ! Unable to get exact match on first try. Quiting.")
        return filepath

    # to fix missing key errors
    for key in {"certificates", "genres", "language codes", "year"}:
        if key not in found:
            found[key] = []

    click.echo(" >> Get 1st result return: {}".format(found["long imdb title"]))
    click.echo(
        "  ! IMDB Id: {}, Title: {}, Year: {}, Kind: {}.".format(
            found.movieID, found["title"], found["year"], found["kind"]
        )
    )
    click.echo(
        "  ! Languages Codes: {}, Genres: {}".format(
            found["language codes"], found["genres"]
        )
    )

    # 1st tier genres
    if is_adult(found["genres"], found["certificates"]):
        filepath = "/Adult"

    # build the rest of the filepath
    filepath = "{}{}/{}.{}{}".format(
        filepath,
        new_path(found),
        found["title"].replace(" ", "."),
        query["year"],
        query["suffix"],
    )
    click.echo("  @ {}".format(filepath))
    return filepath


def unique_path(path, pattern):
    """Generate unique filename. Not used."""

    counter = 0
    while True:
        counter += 1
        new_unique_path = path / pattern.format(counter)
        if not new_unique_path.exists():
            return new_unique_path
