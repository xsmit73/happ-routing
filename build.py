#!/usr/bin/env python3
"""Собирает профиль маршрутизации Happ.

Берёт свежий профиль RoscomVPN DEFAULT, применяет правки из custom.json
и пишет happ-routing.json (+ happ-routing.deeplink для ручного импорта).
LastUpdated меняется только когда реально поменялось содержимое, поэтому
Happ перечитывает профиль лишь при настоящих обновлениях.
"""
import base64
import json
import sys
import time
import urllib.request
from pathlib import Path

UPSTREAM = ("https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/"
            "refs/heads/main/HAPP/DEFAULT.JSON")
ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "happ-routing.json"
OUT_LINK = ROOT / "happ-routing.deeplink"
REQUIRED = ("Geoipurl", "Geositeurl", "DirectSites", "DirectIp", "BlockSites")


def fetch_upstream() -> dict:
    req = urllib.request.Request(UPSTREAM, headers={"User-Agent": "happ-routing-builder"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        sys.exit(f"Upstream profile is missing keys {missing}; not overwriting output")
    return data


def merge(base: list, add: list = (), remove: list = ()) -> list:
    out = [x for x in base if x not in set(remove)]
    for x in add:
        if x not in out:
            out.append(x)
    return out


def build(up: dict, c: dict) -> dict:
    p = dict(up)
    p["Name"] = c.get("name", "RU-direct (auto)")
    p["DirectSites"] = merge(up.get("DirectSites", []), c.get("add_direct_sites", []), c.get("remove_direct_sites", []))
    p["ProxySites"] = merge(up.get("ProxySites", []), c.get("add_proxy_sites", []), c.get("remove_proxy_sites", []))
    p["BlockSites"] = merge(up.get("BlockSites", []), c.get("add_block_sites", []), c.get("remove_block_sites", []))
    p["DirectIp"] = merge(up.get("DirectIp", []), c.get("add_direct_ip", []))
    p["ProxyIp"] = merge(up.get("ProxyIp", []), c.get("add_proxy_ip", []))
    return p


def without_ts(p: dict) -> dict:
    return {k: v for k, v in p.items() if k != "LastUpdated"}


def main() -> None:
    custom = json.loads((ROOT / "custom.json").read_text(encoding="utf-8"))
    upstream = fetch_upstream()
    profile = build(upstream, custom)

    previous = None
    if OUT_JSON.exists():
        previous = json.loads(OUT_JSON.read_text(encoding="utf-8"))

    if previous is not None and without_ts(previous) == without_ts(profile):
        print("No changes")
        return

    # Новая метка всегда больше прежней и не меньше метки upstream.
    stamp = max(int(time.time()),
                int(upstream.get("LastUpdated") or 0),
                int((previous or {}).get("LastUpdated") or 0) + 1)
    profile["LastUpdated"] = str(stamp)

    OUT_JSON.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    compact = json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    OUT_LINK.write_text("happ://routing/onadd/" + base64.b64encode(compact.encode()).decode() + "\n",
                        encoding="utf-8")
    print(f"Updated, LastUpdated={stamp}")


if __name__ == "__main__":
    main()
