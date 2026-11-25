import base64
import html
import json
from pathlib import Path

from .agent import lookup
from .store import data_dir
from .vision import LABELS, MANIFEST


def report(con,rid):
    data = dict(lookup(con,"runs",rid))
    data["model_revision"] = MANIFEST["revision"]
    data["photos"] = []
    for r in con.execute("""SELECT p.id,p.title,p.source_id,p.source_version,p.sha256,p.provenance,
            c.labels,c.state,c.recall FROM cases c JOIN photos p ON p.id=c.photo_id
            WHERE c.run_id=? ORDER BY c.position""",(rid,)):
        p = dict(r)
        p["accepted"] = [dict(id=i,label=LABELS[str(i)]) for i in json.loads(p.pop("labels"))]
        p["recall"] = json.loads(p["recall"])
        p["trials"] = []
        for row in con.execute("""SELECT t.id,t.artifact,t.condition,t.level,t.mass,t.outcome,t.cached,
                 a.transform,a.duration_ms,a.artifact_sha,a.predictions FROM trials t JOIN artifacts a
                 ON a.id=t.artifact WHERE t.run_id=? AND t.photo_id=? ORDER BY t.rowid""",(rid,p["id"])):
            t = dict(row)
            t["predictions"] = json.loads(t["predictions"])
            t["transform"] = json.loads(t["transform"])
            t["image"] = "/api/images/"+t["artifact"]
            p["trials"].append(t)
        data["photos"].append(p)
    data["decisions"] = [dict(photo_id=r["photo_id"],action=r["action"],reason_code=r["reason"],
                         evidence_ids=json.loads(r["evidence"]),budget_remaining=r["remaining"])
                         for r in con.execute("SELECT * FROM decisions WHERE run_id=? ORDER BY rowid",(rid,))]
    data["events"] = [dict(r) for r in con.execute("SELECT provider,method,path,status,duration_ms FROM connector_events WHERE run_id=? ORDER BY rowid",(rid,))]
    data["pending_writes"] = con.execute("SELECT count(*) FROM outbox WHERE run_id=? AND status='pending'",(rid,)).fetchone()[0]
    data["inference_cpu_ms"] = sum(t["duration_ms"] for p in data["photos"] for t in p["trials"] if not t["cached"])
    return data


def standalone(data,image_bytes):
    esc = lambda v:html.escape(str(v))
    parts = ["<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'><title>BlindSpot run report</title>",
             "<style>body{max-width:75rem;margin:2rem auto;padding:0 1rem;font:1rem system-ui;background:#101417;color:#e9efec}article{display:inline-block;vertical-align:top;width:16rem;margin:.5rem}img{width:100%}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>",
             "<h1>BlindSpot · Run report</h1>",f"<p>{esc(data['goal'])} · {esc(data['state'])} · {data['inference_cpu_ms']:.2f} ms inference CPU</p>"]
    for p in data["photos"]:
        parts.append(f"<h2>{esc(p['title'])}</h2><p>{esc(p['provenance'])} · {esc(p['accepted'])}</p>")
        for t in p["trials"]:
            img = base64.b64encode(image_bytes(t)).decode()
            parts.append(f"<article><h3>{esc(t['condition'])} · {t['level']}</h3><img alt='Trial image' src='data:image/png;base64,{img}'><p>{esc(t['outcome'])}</p><ol>")
            for pred in t["predictions"]:
                parts.append(f"<li>{esc(pred['label'])} {pred['score']:.2%}</li>")
            parts.append("</ol></article>")
    parts.append("<details><summary>Full evidence and reproducibility record</summary><pre>"+esc(json.dumps(data,indent=2))+"</pre></details>")
    return "".join(parts)


def save(con,rid):
    dest = data_dir()/"reports"/rid
    dest.mkdir(parents=True,exist_ok=True)
    data = report(con,rid)
    files = {"json":json.dumps(data,indent=2), "html":standalone(data,lambda t:lookup(con,"artifacts",t["artifact"])["image"])}
    for ext,content in files.items():
        path = dest/f"report.{ext}"
        temp = path.with_suffix(".tmp")
        temp.write_text(content)
        temp.replace(path)
    return dest
