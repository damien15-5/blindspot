"""Fresh local API run and optional publish of SAMPLE-only offline replay."""
import argparse
import json
import os
import resource
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from app.main import app
from app.store import database
from app.agent import lookup
from app.vision import sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",required=True,type=Path)
    parser.add_argument("--snapshot",action="store_true")
    args = parser.parse_args()
    args.data.mkdir(parents=True,exist_ok=True)
    if any(args.data.iterdir()):
        parser.error("Select a new empty directory for reproducible measurements")
    secret = secrets.token_urlsafe(32)
    os.environ.update(BLINDSPOT_DATA=str(args.data),BLINDSPOT_MODE="owner",BLINDSPOT_MEMORY="local",BLINDSPOT_OWNER_TOKEN=secret)
    client = TestClient(app,headers={"authorization":"Bearer "+secret})
    def post(path,body=None):
        response = client.post(path,json=body)
        response.raise_for_status()
        return response.json()
    wall,cpu = time.monotonic(),time.process_time()
    runs = []
    for followup in (False,True):
        ids = post("/api/samples"+("?held_out=true" if followup else ""))
        rid = post("/api/runs",dict(photos=ids,seed=42))["id"]
        cursor = 0
        while True:
            run = post(f"/api/runs/{rid}/step",dict(cursor=cursor))
            if run["state"]=="done":
                break
            assert run["cursor"]>cursor
            cursor = run["cursor"]
        runs.append(run)
        print("FOLLOW-UP" if followup else "SAMPLE SET",rid,"CPU ms",round(run["inference_cpu_ms"],3))
        for p in run["photos"]:
            print(p["source_version"],p["title"],[(t["condition"],t["level"],t["predictions"][0]["id"],t["outcome"]) for t in p["trials"]])
        print("TRACE",[(e["provider"],e["method"],e["status"]) for e in run["events"]])
        print("ORDER CHANGES",[d for d in run["decisions"] if d["reason_code"]=="RECALLED_FAILURE"])
    print("wall_s",round(time.monotonic()-wall,3),"process_cpu_s",round(time.process_time()-cpu,3),
          "max_rss_kib",resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          "persistent_bytes",sum(p.stat().st_size for p in args.data.rglob("*") if p.is_file()))
    if args.snapshot:
        dest = ROOT/"demo"
        (dest/"images").mkdir(parents=True,exist_ok=True)
        with database() as con:
            for run,name in zip(runs,("session","followup")):
                for p in run["photos"]:
                    assert p["provenance"].startswith("SAMPLE")
                    for t in p["trials"]:
                        data = lookup(con,"artifacts",t["artifact"])["image"]
                        assert sha(data)==t["artifact_sha"]
                        image = dest/"images"/(t["artifact_sha"]+".png")
                        image.write_bytes(data)
                        t["image"]="/demo/images/"+image.name
                (dest/(name+".json")).write_text(json.dumps(run,indent=2)+"\n")


if __name__=="__main__":
    main()
