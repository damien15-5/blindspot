import hmac
import json
import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import UnidentifiedImageError

from . import agent, box, connectors, reports
from .store import database, labels, photo
from .vision import LABELS, ROOT

app = FastAPI(title="BlindSpot",docs_url=None,redoc_url=None,openapi_url=None)


def allowed(request):
    secret = os.getenv("BLINDSPOT_OWNER_TOKEN","")
    return bool(os.getenv("BLINDSPOT_MODE","demo")=="owner" and secret and
                hmac.compare_digest(request.headers.get("authorization","").encode(),("Bearer "+secret).encode()))


def owner(request:Request):
    if not allowed(request):
        raise HTTPException(403,"Owner access required")


auth = [Depends(owner)]


@app.exception_handler(ValueError)
@app.exception_handler(UnidentifiedImageError)
async def invalid(request,exc):
    return JSONResponse({"detail":str(exc)},status_code=422)


@app.exception_handler(KeyError)
async def missing(request,exc):
    return JSONResponse({"detail":"Record or required field missing"},status_code=404)


@app.get("/api/status")
def status(request:Request):
    return dict(owner=allowed(request),mode=os.getenv("BLINDSPOT_MODE","demo"),
                memory=connectors.provider(),box=os.getenv("BLINDSPOT_BOX")=="1")


@app.get("/api/library",dependencies=auth)
def library():
    with database() as con:
        photos = [dict(r) for r in con.execute("SELECT id,title,accepted,provenance FROM photos ORDER BY rowid DESC")]
        return dict(photos=photos,runs=[dict(r) for r in con.execute("SELECT id,state,goal FROM runs ORDER BY rowid DESC")])


@app.get("/api/classes",dependencies=auth)
def classes():
    return LABELS


@app.post("/api/import",dependencies=auth)
def upload(file:Annotated[UploadFile,File()],accepted:Annotated[str,Form()]="[]"):
    data = file.file.read(2*1024**2+1)
    with database() as con:
        return dict(id=photo(con,data,(file.filename or "Photo")[:180],"local:"+(file.filename or "Photo")[:180],"1","Owner · upload",json.loads(accepted)))


@app.post("/api/samples",dependencies=auth)
def samples(held_out:bool=False):
    folder = ROOT/"samples"
    items = json.loads((folder/("held-out.json" if held_out else "labels.json")).read_text())
    with database() as con:
        return [photo(con,(folder/i["file"]).read_bytes(),i["title"],i["source"],i["version"],i["provenance"],i["accepted"]) for i in items]


@app.post("/api/box/import",dependencies=auth)
def box_import():
    with database() as con:
        try:
            ids = box.intake(con)
        except connectors.Unavailable as e:
            return JSONResponse({"detail":str(e)},status_code=503)
        return ids


class Label(BaseModel):
    accepted:list[int] = Field(max_length=1000,strict=True)


@app.post("/api/photos/{pid}/label",dependencies=auth)
def label(pid:str,body:Label):
    with database() as con:
        agent.relabel(con,pid,labels(body.accepted))
    return {"saved":True}


class Run(BaseModel):
    photos:list[str] = Field(min_length=1,max_length=12)
    seed:int = Field(default=42,ge=0,le=2147483647)
    budget:int = Field(default=72,ge=1,le=72)
    goal:str = Field(default="Find camera conditions that change my inventory labels",max_length=240)


@app.post("/api/runs",dependencies=auth)
def create(body:Run):
    with database() as con:
        return {"id":agent.create(con,body.photos,body.seed,body.budget,body.goal)}


class Step(BaseModel):
    cursor:int = Field(ge=0)


@app.post("/api/runs/{rid}/step",dependencies=auth)
def step(rid:str,body:Step):
    with database() as con:
        queued = agent.step(con,rid,body.cursor)
    # The trial and outbox intent must survive a crash before a provider sees a write.
    with database() as con:
        if queued:
            row = agent.lookup(con,"outbox",queued)
            if row["status"]=="pending":
                try:
                    connectors.deliver(con,row)
                except connectors.Unavailable:
                    pass  # The durable intent and redacted trace remain inspectable.
        data = reports.report(con,rid)
        if data["state"]=="done" and not (reports.data_dir()/"reports"/rid/"report.html").exists():
            reports.save(con,rid)
        return data


@app.post("/api/runs/{rid}/retry",dependencies=auth)
def retry(rid:str):
    with database() as con:
        for row in con.execute("SELECT * FROM outbox WHERE run_id=? AND status='pending' LIMIT 1",(rid,)):
            try:
                connectors.deliver(con,row)
            except connectors.Unavailable as e:
                return JSONResponse({"detail":str(e)},status_code=503)
        return reports.report(con,rid)


@lru_cache(maxsize=1)
def sample_reports():
    return [json.loads((ROOT/"demo"/(name+".json")).read_text()) for name in ("session","followup")]


@app.get("/api/runs/{rid}")
@app.get("/api/report/{rid}")
def get_report(rid:str,request:Request):
    if not allowed(request):
        for data in sample_reports():
            if data["id"]==rid:
                return data
        raise HTTPException(404,"Sample run not found")
    with database() as con:
        return reports.report(con,rid)


@app.get("/api/trials/{tid}")
def get_trial(tid:str,request:Request):
    if not allowed(request):
        for data in sample_reports():
            for p in data["photos"]:
                for t in p["trials"]:
                    if t["id"]==tid:
                        return t
        raise HTTPException(404,"Sample trial not found")
    with database() as con:
        row = agent.lookup(con,"trials",tid)
        data = reports.report(con,row["run_id"])
        return next(t for p in data["photos"] for t in p["trials"] if t["id"]==tid)


@app.get("/api/images/{key}",dependencies=auth)
def image(key:str):
    with database() as con:
        return Response(agent.lookup(con,"artifacts",key)["image"],media_type="image/png")


class Export(BaseModel):
    run_id:str
    destination:str="local"


@app.post("/api/export",dependencies=auth)
def export(body:Export):
    with database() as con:
        dest = reports.save(con,body.run_id)
        if body.destination=="box":
            try:
                return {"box_file_id":box.export(con,body.run_id,dest/"report.html")}
            except connectors.Unavailable as e:
                return JSONResponse({"detail":str(e)},status_code=503)
        if body.destination!="local":
            raise ValueError("Unknown destination")
        return FileResponse(dest/"report.html",filename="BlindSpot-report.html")


app.mount("/demo",StaticFiles(directory=ROOT/"demo",check_dir=False),name="demo")
app.mount("/",StaticFiles(directory=ROOT/"web/dist",html=True,check_dir=False),name="ui")
