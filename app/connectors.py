"""Identity comes from the Sprite gateway. Only configured provider routes are callable."""
import json
import logging
import os
import re
import time

import httpx
import numpy as np

from .vision import MODEL

LOCAL = "LOCAL/MOCK"
NAMESPACE = "blindspot-demo"
OWNER = "Damien"


class Unavailable(Exception):
    pass


def provider():
    value = os.getenv("BLINDSPOT_MEMORY","local")
    if value not in ("local","pinecone"):
        raise ValueError("Unknown memory provider")
    return "Pinecone" if value=="pinecone" else LOCAL


def event(con, run, name, method, path, status, start):
    ms = (time.monotonic()-start)*1000
    con.execute("INSERT INTO connector_events VALUES(?,?,?,?,?,?)",(run,name,method,path,str(status),ms))
    logging.getLogger("blindspot").info("%s %s %s %s %.2fms",name,method,path,status,ms)


def gateway(con, run, service, method, path, redacted, **kwargs):
    start = time.monotonic()
    base = os.getenv(f"BLINDSPOT_{service.upper()}_URL","").rstrip("/")
    if not re.fullmatch(r"https://api\.sprites\.dev/v1/gateway/"+service+r"/[A-Za-z0-9_-]+",base):
        event(con,run,service,method,redacted,"unconfigured",start)
        raise Unavailable(f"{service} gateway is unconfigured")
    try:
        response = httpx.request(method,base+path,timeout=4,follow_redirects=False,**kwargs)
    except httpx.RequestError:
        event(con,run,service,method,redacted,"network_error",start)
        raise Unavailable(f"{service} gateway unavailable") from None
    event(con,run,service,method,redacted,response.status_code,start)
    if not response.is_success:
        raise Unavailable(f"{service} gateway returned {response.status_code}")
    return response


def signature(probs):
    return np.asarray(probs/np.linalg.norm(probs),dtype=np.float32)


def remote(con, run, operation, body):
    index = os.getenv("BLINDSPOT_INDEX","blindspot-memory")
    if not re.fullmatch(r"[a-z0-9-]{1,45}",index):
        raise ValueError("Invalid Pinecone index")
    return gateway(con,run,"pinecone","POST",f"/indexes/{index}/{operation}",
                   f"/indexes/<index>/{operation}",json={"namespace":NAMESPACE,**body})


def recall(con, run, vector):
    start = time.monotonic()
    if provider()==LOCAL:
        rows = con.execute("SELECT * FROM memory WHERE model=? AND owner=?", (MODEL,OWNER))
        hits = [dict(id=r["id"],score=float(vector @ np.frombuffer(r["vector"],np.float32)),
                     metadata=json.loads(r["metadata"])) for r in rows]
        event(con,run,LOCAL,"QUERY","/memory","ok",start)
        return sorted(hits,key=lambda r:(-r["score"],r["id"]))[:3]
    res = remote(con,run,"query",dict(vector=vector.tolist(),topK=3,includeMetadata=True,
                 filter={"model":{"$eq":MODEL},"owner":{"$eq":OWNER}}))
    try:
        hits = res.json()["matches"]
        return [dict(id=str(h["id"]),score=float(h["score"]),metadata=h["metadata"]) for h in hits
                if isinstance(h["metadata"],dict)][:3]
    except (ValueError,KeyError,TypeError):
        raise Unavailable("Malformed Pinecone query response") from None


def deliver(con, row):
    if row["provider"]!=provider():
        raise Unavailable("Select the original provider to retry this failure")
    item = json.loads(row["payload"])
    if provider()==LOCAL:
        start = time.monotonic()
        con.execute("INSERT OR REPLACE INTO memory VALUES(?,?,?,?,?)",
                    (item["id"],MODEL,OWNER,np.array(item["values"],np.float32).tobytes(),
                     json.dumps(item["metadata"])))
        event(con,row["run_id"],LOCAL,"UPSERT","/memory","ok",start)
    else:
        res = remote(con,row["run_id"],"vectors/upsert",dict(vectors=[item]))
        try:
            if res.json()["upsertedCount"] != 1:
                raise ValueError()
        except (KeyError,TypeError,ValueError):
            raise Unavailable("Pinecone did not acknowledge one vector") from None
    con.execute("UPDATE outbox SET status='sent' WHERE id=?", (row["id"],))
