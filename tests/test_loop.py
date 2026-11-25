import json
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app
from app.vision import ROOT
from app.store import database
from app.agent import next_test
from conftest import upload,begin,advance


def test_policy_changes_order_and_escalates_largest_drop():
    assert next_test([],[],42)[:2]==("blur",1)
    case=dict(score=.8,id="r:p",metadata={"condition":"low light"})
    assert next_test([],[case],42)==("low light",1,"RECALLED_FAILURE",["r:p"])
    assert next_test([],[{**case,"score":.05}],42)[:2]==("blur",1)
    trials=[dict(id=c,level=1,condition=c,mass=m) for c,m in
            [("blur",.9),("low light",.1),("JPEG",.6),("colour cast",.4)]]
    assert next_test(trials,[],42)==("low light",2,"LARGEST_LABEL_DROP",["low light"])


def test_resume_and_concurrent_retries(client,guitar):
    pid=upload(client,guitar)
    rid=begin(client,pid,budget=1)
    assert client.post("/api/runs",json={"photos":[pid]}).status_code==422
    with ThreadPoolExecutor(2) as pool:
        replies=list(pool.map(lambda _:advance(client,rid,0),range(2)))
    assert all(r["cursor"]==1 for r in replies)
    reopened=TestClient(app,headers=client.headers)
    done=advance(reopened,rid,1)
    assert done["state"]=="done" and len(done["photos"][0]["trials"])==2
    assert advance(client,rid,1)["cursor"]==2
    again=begin(client,pid,1)
    advance(client,again,0)
    cached=advance(client,again,1)
    assert cached["inference_cpu_ms"]==0 and all(t["cached"] for t in cached["photos"][0]["trials"])
    with database() as con:
        assert con.execute("SELECT count(*) FROM artifacts").fetchone()[0]==2


def test_retrieval_on_distinct_followup(client,guitar):
    rid=begin(client,upload(client,guitar),6)
    for n in range(7):
        original=advance(client,rid,n)
    assert original["state"]=="done"
    assert any(t["outcome"]=="induced error" for t in original["photos"][0]["trials"])
    pid=client.post("/api/samples?held_out=true").json()[0]
    new=begin(client,pid,1)
    advance(client,new,0)
    second=advance(client,new,1)
    p=second["photos"][0]
    assert p["trials"][1]["condition"]=="low light" and p["trials"][1]["outcome"]=="accepted"
    assert any(d["reason_code"]=="RECALLED_FAILURE" for d in second["decisions"])
    assert all(e["provider"]=="LOCAL/MOCK" for e in second["events"])


def test_ask_label_and_retake(client,guitar):
    pid=upload(client,guitar,"[]")
    rid=begin(client,pid)
    ask=advance(client,rid,0)
    assert ask["decisions"][-1]["action"]=="ASK_LABEL" and not ask["photos"][0]["trials"]
    assert advance(client,rid,1)["cursor"]==1
    assert client.post(f"/api/photos/{pid}/label",json={"accepted":[1000]}).status_code==422
    assert client.post(f"/api/photos/{pid}/label",json={"accepted":[883]}).status_code==200
    done=advance(client,rid,1)
    assert done["state"]=="done" and done["decisions"][-1]["action"]=="REQUEST_RETAKE"
    assert done["photos"][0]["trials"][0]["outcome"]=="baseline error" and not done["events"]


def test_report_and_hashes(client,guitar):
    rid=begin(client,upload(client,guitar),1)
    advance(client,rid,0)
    data=advance(client,rid,1)
    from app.vision import sha
    for t in data["photos"][0]["trials"]:
        assert sha(client.get(t["image"]).content)==t["artifact_sha"]
        assert client.get("/api/trials/"+t["id"]).json()["predictions"]==t["predictions"]
    assert client.get("/api/report/"+rid).json()["id"]==rid
    html=client.post("/api/export",json={"run_id":rid}).text
    assert "data:image/png;base64," in html and data["model_sha"] in html and "MILD_PROBE" in html


def test_intake_limits(client,guitar):
    for content in (b"invalid",b"0"*(2*1024**2+1)):
        assert client.post("/api/import",files={"file":("f.jpg",content)}).status_code==422
    assert upload(client,guitar)==upload(client,guitar)
    assert client.post("/api/runs",json={"photos":["x"]*13}).status_code==422


def test_public_replay_cannot_access_private_or_mutate(client,guitar,monkeypatch):
    rid=begin(client,upload(client,guitar))
    monkeypatch.setenv("BLINDSPOT_MODE","demo")
    data=client.get("/demo/session.json").json()
    assert client.get("/api/report/"+data["id"]).json()==data
    assert client.get("/api/report/"+rid).status_code==404
    assert client.get("/api/library").status_code==403
    paths={"/api/import":None,"/api/samples":None,"/api/box/import":None,
           "/api/runs":{"photos":["x"]},f"/api/runs/{rid}/step":{"cursor":0},
           f"/api/runs/{rid}/retry":None,"/api/photos/x/label":{"accepted":[402]},
           "/api/export":{"run_id":rid}}
    for path,body in paths.items():
        assert client.post(path,json=body).status_code==403,path
    assert TestClient(app).get("/api/status").json()["owner"] is False
