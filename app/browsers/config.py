from dataclasses import dataclass, field


@dataclass
class Config:
    @dataclass
    class HumbleBundle:
        formats = (".pdf", ".epub", ".cbz", ".mobi")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
            "Referer": "https://www.humblebundle.com/downloads",
        }
        api: str = "https://www.humblebundle.com/api/v1/order/{id}?all_tpkds=true"
        library: str = "https://www.humblebundle.com/api/v1/user/order"

        download_location: str = "./run/humblebundle/"

    hb: HumbleBundle = field(default_factory=list)
