import socket
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.vision import ROOT


@pytest.fixture(autouse=True)
def isolate(monkeypatch,tmp_path):
    def forbidden(*args,**kwargs):
        raise AssertionError("Unit tests cannot use the network")
    monkeypatch.setattr(socket.socket,"connect",forbidden)
    monkeypatch.setattr(socket.socket,"connect_ex",forbidden)
    monkeypatch.setattr(socket,"getaddrinfo",forbidden)
    monkeypatch.setenv("BLINDSPOT_DATA",str(tmp_path))
    monkeypatch.setenv("BLINDSPOT_MEMORY","local")
    monkeypatch.setenv("BLINDSPOT_MODE","owner")
    monkeypatch.setenv("BLINDSPOT_OWNER_TOKEN","unit-owner")
    monkeypatch.delenv("BLINDSPOT_BOX",raising=False)


@pytest.fixture
def client():
    return TestClient(app,headers={"Authorization":"Bearer unit-owner"})


@pytest.fixture
def guitar():
    return (ROOT/"samples/guitar-98679.jpg").read_bytes()


def upload(client,data,accepted="[402]"):
    r = client.post("/api/import",files={"file":("guitar.jpg",data,"image/jpeg")},data={"accepted":accepted})
    r.raise_for_status()
    return r.json()["id"]


def begin(client,pid,budget=6):
    r = client.post("/api/runs",json={"photos":[pid],"budget":budget})
    r.raise_for_status()
    return r.json()["id"]


def advance(client,rid,cursor):
    r = client.post(f"/api/runs/{rid}/step",json={"cursor":cursor})
    r.raise_for_status()
    return r.json()
