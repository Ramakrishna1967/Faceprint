from dataclasses import asdict, dataclass
import json
import os
from urllib.parse import quote

import requests


@dataclass
class Candidate:
    url: str
    image_url: str
    title: str = ""
    source: str = ""


class SerpApiLens:
    def __init__(self, api_key=None, timeout=30):
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        self.timeout = timeout

    def search(self, image_url: str) -> list[Candidate]:
        if not self.api_key:
            raise RuntimeError("SERPAPI_KEY is required")
        response = requests.get(
            "https://serpapi.com/search.json?engine=google_lens&url="
            + quote(image_url, safe="")
            + "&api_key="
            + quote(self.api_key, safe=""),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return [Candidate(x.get("link", ""), x.get("thumbnail", ""), x.get("title", ""), x.get("source", ""))
                for x in data.get("visual_matches", []) if x.get("link") and x.get("thumbnail")]


def save_candidates(path, candidates):
    path.write_text(json.dumps([asdict(c) for c in candidates], indent=2), encoding="utf-8")
