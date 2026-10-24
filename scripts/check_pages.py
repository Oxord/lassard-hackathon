"""Check the public showroom HTML and its entry assets; no GitHub login needed."""

import argparse
from html.parser import HTMLParser
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


class EntryPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_app = False
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.has_app |= attrs.get("id") == "app"
        if tag == "script" and attrs.get("type") == "module" and attrs.get("src"):
            self.assets.append((attrs["src"], "javascript"))
        if tag == "link" and "stylesheet" in attrs.get("rel", "").split() and attrs.get("href"):
            self.assets.append((attrs["href"], "css"))


def fetch(url, timeout):
    request = Request(url, headers={"User-Agent": "lassard-pages-check/1.0"})
    with urlopen(request, timeout=timeout) as response:
        data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError("Response exceeds 4 MiB")
        return response.geturl(), response.headers.get_content_type(), data


def check(url, timeout=15):
    report = {"url": url, "ok": False, "assets": [], "errors": []}
    try:
        if urlsplit(url).scheme not in ("http", "https"):
            raise ValueError("URL must use HTTP or HTTPS")
        final_url, content_type, data = fetch(url, timeout)
        report["final_url"] = final_url
        if content_type != "text/html":
            raise ValueError("Entry page is not HTML: " + content_type)
        page = EntryPage()
        page.feed(data.decode("utf-8-sig"))
        if not page.has_app:
            report["errors"].append("Showroom container #app is missing")
        if not any(kind == "javascript" for _, kind in page.assets):
            report["errors"].append("No module entry script found")
        for source, kind in dict.fromkeys(page.assets):
            asset_url = urljoin(final_url, source)
            asset = {"url": asset_url, "kind": kind, "ok": False}
            report["assets"].append(asset)
            try:
                if urlsplit(asset_url).scheme not in ("http", "https"):
                    raise ValueError("Asset URL must use HTTP or HTTPS")
                _, mime, body = fetch(asset_url, timeout)
                expected = {"text/javascript", "application/javascript"} if kind == "javascript" else {"text/css"}
                if mime not in expected or not body.strip():
                    raise ValueError("Empty asset or incorrect Content-Type: " + mime)
                if body.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                    raise ValueError("Asset returned an HTML page")
                asset.update(ok=True, bytes=len(body), content_type=mime)
            except (HTTPError, URLError, OSError, ValueError) as error:
                asset["error"] = str(error)
                report["errors"].append(asset_url + ": " + str(error))
    except (HTTPError, URLError, OSError, ValueError) as error:
        report["errors"].append(str(error))
    report["ok"] = not report["errors"]
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="https://oxord.github.io/lassard-hackathon/")
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    result = check(args.url, args.timeout)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
