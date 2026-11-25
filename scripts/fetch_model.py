"""Fetch public model bytes only after verifying their immutable digest."""

import hashlib
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "models"
manifest = json.loads((root / "manifest.json").read_text())
for name, digest in manifest["files"].items():
    dest = root / Path(name).name
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == digest:
        continue
    url = f"{manifest['repo']}/resolve/{manifest['revision']}/{name}"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"Digest mismatch for {name}")
    dest.write_bytes(data)
