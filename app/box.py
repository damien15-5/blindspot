"""Optional Box transport; set path templates from the connection's API Usage panel."""
import json
import os
import re
from pathlib import Path

from .connectors import Unavailable, gateway
from .store import photo, uid, labels

LIMIT = 2*1024**2


def route(key, **ids):
    if os.getenv("BLINDSPOT_BOX")!="1":
        raise ValueError("Box intake and export are disabled")
    template = os.getenv("BLINDSPOT_BOX_"+key+"_PATH","")
    if not template.startswith("/") or any(c in template for c in ("?", "#","..","//")):
        raise ValueError(f"Configure the verified Box {key.lower()} path")
    if any(not re.fullmatch(r"[0-9]+",str(v)) for v in ids.values()):
        raise ValueError("Expected a numeric Box identifier")
    return template.format(**ids)


def intake(con):
    folder = os.getenv("BLINDSPOT_BOX_INPUT","")
    path = route("LIST",folder=folder)
    response = gateway(con,"intake","box","GET",path,"/folders/<input>/items",
                       params={"limit":100,"fields":"id,name,type,file_version,size"})
    listing = response.json()
    entries = listing["entries"]
    if listing.get("total_count",len(entries))>len(entries):
        raise ValueError("Use a dedicated input folder with at most 100 entries")
    files = {x["name"]:x for x in entries if x["type"]=="file"}
    def download(item,limit):
        if item.get("size",limit+1)>limit:
            raise ValueError("Box file exceeds intake limit")
        res = gateway(con,"intake","box","GET",route("DOWNLOAD",file=item["id"]),"/files/<id>/content")
        if len(res.content)>limit:
            raise ValueError("Box response exceeds intake limit")
        return res.content
    if "labels.json" not in files:
        raise ValueError("Box folder needs labels.json")
    items = json.loads(download(files["labels.json"],32768))
    if not isinstance(items,list) or not 1<=len(items)<=12:
        raise ValueError("Provide 1–12 label entries")
    result = []
    for item in items:
        f = files.get(item["file"])
        if not f or not f["name"].lower().endswith((".png",".jpg",".jpeg",".webp")):
            raise ValueError("Label entry does not identify a supported image")
        version = f["file_version"]["id"]
        source = "box:"+f["id"]
        cached = con.execute("SELECT original FROM photos WHERE source_id=? AND source_version=?",(source,version)).fetchone()
        data = cached[0] if cached else download(f,LIMIT)
        pid = photo(con,data,f["name"],source,version,"Owner · Box labels.json",item["accepted"])
        con.execute("UPDATE photos SET accepted=? WHERE id=?", (json.dumps(labels(item["accepted"])), pid))
        result.append(pid)
    return result


def export(con,rid,path):
    folder = os.getenv("BLINDSPOT_BOX_OUTPUT","")
    if not folder.isdecimal():
        raise ValueError("Configure a Box output folder ID")
    name = f"BlindSpot-{rid[:8]}-{uid()}.html"
    attrs = json.dumps(dict(name=name,parent=dict(id=folder)))
    response = gateway(con,rid,"box","POST",route("UPLOAD"),"/files/content",
                       data={"attributes":attrs},files={"file":(name,path.read_bytes(),"text/html")})
    return response.json()["entries"][0]["id"]
