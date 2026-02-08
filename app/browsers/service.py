import asyncio
import sqlite3

from pathlib import Path

import browser_cookie3
import httpx

from click import Context
from werkzeug.utils import secure_filename

from . import logger
from .config import Config


class Browser:
    def __init__(self, configs: Config, context: Context):
        self.configs = configs
        self.context = context

    def get_bookmarks(PROFILE_DB):
        con = sqlite3.connect(PROFILE_DB)
        cur = con.cursor()
        cur.execute(
            """
            SELECT moz_places.url, moz_bookmarks.title
            FROM moz_bookmarks
            JOIN moz_places ON moz_bookmarks.fk = moz_places.id
            WHERE moz_places.url LIKE 'http%'
        """
        )
        results = cur.fetchall()
        con.close()
        return results

    async def check_url(client, url, semaphore):
        async with semaphore:
            try:
                resp = await client.get(url, timeout=10)
                return url, resp.status_code
            except Exception as e:
                return url, f"error: {e}"

    async def parse(self):
        # Locate Firefox profile (adjust path for your OS)
        FIREFOX_PROFILE = Path.home() / ".mozilla/firefox"
        PROFILE_DB = None

        # Find the first profile with places.sqlite
        for profile in FIREFOX_PROFILE.glob("*.default*"):
            candidate = profile / "places.sqlite"
            if candidate.exists():
                PROFILE_DB = candidate
                break

        if not PROFILE_DB:
            raise FileNotFoundError(
                "places.sqlite not found. Make sure Firefox profile exists."
            )

        bookmarks = self.get_bookmarks(PROFILE_DB)
        logger.info(f"Found {len(bookmarks)} bookmarks")

        semaphore = asyncio.Semaphore(20)  # limit concurrency to 20
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [self.check_url(client, url, semaphore) for url, _ in bookmarks]

            for future in asyncio.as_completed(tasks):
                url, status = await future
                if status == 404:
                    logger.info(f"[404] {url}")
                elif isinstance(status, int) and status >= 400:
                    logger.info(f"[{status}] {url}")
                elif isinstance(status, str):
                    logger.info(f"[ERR] {url} -> {status}")

    def run(self, humblebundle, target, list):
        if humblebundle:
            self.get_hb_download()
            return

        if list:
            return

        if target:
            return

        asyncio.run(self.parse())

    def get_hb_download(self):
        cj = browser_cookie3.edge(domain_name="humblebundle.com")

        resp = httpx.get(
            self.configs.hb.library, cookies=cj, headers=self.configs.hb.headers
        )
        resp.raise_for_status()

        for order_id in resp.json():
            resp = httpx.get(
                self.configs.hb.api.replace("{id}", order_id),
                cookies=cj,
                headers=self.configs.hb.headers,
            )
            resp.raise_for_status()

            order = resp.json()

            bundle_name = order.get("product", {}).get("human_name", "UnknownBundle")
            bundle_dir = self.configs.hb.download_location / secure_filename(
                bundle_name
            )
            bundle_dir.mkdir(exist_ok=True)

            for sub in order.get("subproducts", []):
                title = sub.get("human_name", "Untitled")
                for dl in sub.get("downloads", []):
                    for file in dl.get("download_struct", []):
                        fname = file.get("name", "")
                        if fname.lower().endswith(self.configs.hb.formats):
                            url = file["url"]["web"]
                            filename = secure_filename(bundle_dir / fname)

                            """Download file from URL to filename."""
                            if filename.exists():
                                logger.info(f"✅ Already downloaded: {filename}")
                                return
                            logger.info(f"⬇️ Downloading {filename.name} ...")
                            # with httpx.get(
                            #     url,
                            #     cookies=cj,
                            #     headers=self.configs.hb.headers,
                            #     stream=True,
                            # ) as r:
                            #     r.raise_for_status()
                            #     with open(filename, "wb") as f:
                            #         for chunk in r.iter_content(8192):
                            #             f.write(chunk)

        logger.info(
            "\n🎉 Done! All ebooks saved to",
            Path(self.configs.hb.download_location).resolve(),
        )


# firefox
# SELECT datetime(moz_historyvisits.visit_date/1000000, 'unixepoch', 'localtime'), moz_places.url FROM moz_places, moz_historyvisits WHERE moz_places.id = moz_historyvisits.place_id;
# datetime(moz_historyvisits.visit_date/1000000, 'unixepoch', 'localtime')	url
# 2017-07-19 21:50:49	https://addons.mozilla.org/en-US/firefox/addon/adblock-plus-pop-up-addon/
#
