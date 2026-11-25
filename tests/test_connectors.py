import json
import httpx
import numpy as np
import pytest
from app import box, connectors as m
from app.store import database
from app.vision import MODEL
from conftest import upload,begin,advance


@pytest.mark.parametrize("status",[403,429,503])
def test_remote_failure_is_traced_without_local_fallback(client,guitar,monkeypatch,status):
    monkeypatch.setenv("BLINDSPOT_MEMORY","pinecone")
    monkeypatch.setenv("BLINDSPOT_PINECONE_URL","https://api.sprites.dev/v1/gateway/pinecone/conn_private")
    monkeypatch.setattr(httpx,"request",lambda *a,**kw:httpx.Response(status))
    rid=begin(client,upload(client,guitar),2)
    base=advance(client,rid,0)
    assert base["decisions"][-1]["reason_code"]=="REMOTE_MEMORY_UNAVAILABLE"
    advance(client,rid,1)
    done=advance(client,rid,2)
    assert done["pending_writes"]==1
    assert all(e["status"]==str(status) and "conn_private" not in e["path"] for e in done["events"])
    assert client.post("/api/runs/"+rid+"/retry").status_code==503
    seen=[]
    def acknowledge(method,url,**kw):
        seen.append(kw["json"]["vectors"][0]["id"])
        assert url.endswith("/indexes/blindspot-memory/vectors/upsert")
        return httpx.Response(200,json={"upsertedCount":1})
    monkeypatch.setattr(httpx,"request",acknowledge)
    assert client.post("/api/runs/"+rid+"/retry").json()["pending_writes"]==0
    client.post("/api/runs/"+rid+"/retry")
    assert len(seen)==1


def test_gateway_query_shape(monkeypatch):
    monkeypatch.setenv("BLINDSPOT_MEMORY","pinecone")
    monkeypatch.setenv("BLINDSPOT_PINECONE_URL","https://api.sprites.dev/v1/gateway/pinecone/conn_test")
    def fake(method,url,**kw):
        assert method=="POST" and url.endswith("conn_test/indexes/blindspot-memory/query")
        body=kw["json"]
        assert body["namespace"]=="blindspot-demo" and body["filter"]["model"]["$eq"]==MODEL
        assert body["filter"]["owner"]["$eq"]=="Damien" and len(body["vector"])==1000 and body["topK"]==3
        assert "headers" not in kw
        return httpx.Response(200,json={"matches":[dict(id="r:p",score=.86,metadata={"condition":"blur"})]})
    monkeypatch.setattr(httpx,"request",fake)
    with database() as con:
        assert m.recall(con,"run",m.signature(np.ones(1000)))[0]["id"]=="r:p"


def test_network_and_malformed_errors(monkeypatch):
    monkeypatch.setenv("BLINDSPOT_MEMORY","pinecone")
    with database() as con:
        with pytest.raises(m.Unavailable):m.recall(con,"run",np.ones(1000))
        monkeypatch.setenv("BLINDSPOT_PINECONE_URL","https://api.sprites.dev/v1/gateway/pinecone/conn_test")
        def timeout(*a,**k):raise httpx.ReadTimeout("timeout")
        monkeypatch.setattr(httpx,"request",timeout)
        with pytest.raises(m.Unavailable):m.recall(con,"run",np.ones(1000))
        monkeypatch.setattr(httpx,"request",lambda *a,**k:httpx.Response(200,json={}))
        with pytest.raises(m.Unavailable):m.recall(con,"run",np.ones(1000))


def test_box_import_cache_and_export(monkeypatch,guitar,client):
    for key,v in dict(BOX="1",BOX_URL="https://api.sprites.dev/v1/gateway/box/conn_test",BOX_INPUT="42",BOX_OUTPUT="43",
                      BOX_LIST_PATH="/folders/{folder}/items",BOX_DOWNLOAD_PATH="/files/{file}/content",BOX_UPLOAD_PATH="/files/content").items():
        monkeypatch.setenv("BLINDSPOT_"+key,v)
    downloaded=[]
    def fake(method,url,**kw):
        if url.endswith("/folders/42/items"):
            return httpx.Response(200,json={"entries":[dict(type="file",id=i,name=n,size=s,file_version={"id":"1"})
                                  for i,n,s in [("1","labels.json",60),("2","photo.jpg",len(guitar))]]})
        if url.endswith("/files/1/content"):
            return httpx.Response(200,json=[{"file":"photo.jpg","accepted":[402]}])
        if url.endswith("/files/2/content"):
            downloaded.append(True)
            return httpx.Response(200,content=guitar)
        assert method=="POST" and json.loads(kw["data"]["attributes"])["parent"]["id"]=="43"
        assert kw["files"]["file"][1].startswith(b"<!doctype html>")
        return httpx.Response(201,json={"entries":[{"id":"123"}]})
    monkeypatch.setattr(httpx,"request",fake)
    ids=client.post("/api/box/import").json()
    assert ids==client.post("/api/box/import").json() and len(downloaded)==1
    rid=begin(client,ids[0],1)
    advance(client,rid,0)
    assert client.post("/api/export",json={"run_id":rid,"destination":"box"}).json()=={"box_file_id":"123"}
