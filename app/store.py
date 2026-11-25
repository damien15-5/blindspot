import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .vision import ROOT, decode, sha

SCHEMA = """
CREATE TABLE IF NOT EXISTS photos(
 id TEXT PRIMARY KEY, title TEXT, source_id TEXT, source_version TEXT, provenance TEXT,
 sha256 TEXT, accepted TEXT, original BLOB, UNIQUE(source_id,source_version,sha256));
CREATE TABLE IF NOT EXISTS runs(
 id TEXT PRIMARY KEY, goal TEXT, model_sha TEXT, preprocessing_sha TEXT, state TEXT,
 seed INTEGER, budget INTEGER, cursor INTEGER DEFAULT 0, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS active ON runs(state) WHERE state='active';
CREATE TABLE IF NOT EXISTS cases(
 run_id TEXT, photo_id TEXT, position INTEGER, labels TEXT, state TEXT DEFAULT 'new',
 recall TEXT DEFAULT '[]', PRIMARY KEY(run_id,photo_id));
CREATE TABLE IF NOT EXISTS artifacts(
 id TEXT PRIMARY KEY, transform TEXT, predictions TEXT, probs BLOB, duration_ms REAL,
 artifact_sha TEXT, image BLOB);
CREATE TABLE IF NOT EXISTS trials(
 id TEXT PRIMARY KEY, run_id TEXT, photo_id TEXT, artifact TEXT, condition TEXT,
 level INTEGER, mass REAL, outcome TEXT, cached INTEGER,
 UNIQUE(run_id,photo_id,condition,level));
CREATE TABLE IF NOT EXISTS decisions(
 run_id TEXT, photo_id TEXT, action TEXT, reason TEXT, evidence TEXT, remaining INTEGER);
CREATE TABLE IF NOT EXISTS connector_events(
 run_id TEXT, provider TEXT, method TEXT, path TEXT, status TEXT, duration_ms REAL);
CREATE TABLE IF NOT EXISTS memory(
 id TEXT PRIMARY KEY, model TEXT, owner TEXT, vector BLOB, metadata TEXT);
CREATE TABLE IF NOT EXISTS outbox(
 id TEXT PRIMARY KEY, run_id TEXT, photo_id TEXT, provider TEXT, payload TEXT, status TEXT);
"""


def data_dir():
    return Path(os.environ.get("BLINDSPOT_DATA", ROOT / "data"))


@contextmanager
def database():
    directory = data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(directory/"agent.sqlite", timeout=8)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.commit()
    finally:
        con.close()


def uid():
    return uuid.uuid4().hex


def labels(values):
    if not isinstance(values,list) or any(type(i) is not int or not 0<=i<1000 for i in values):
        raise ValueError("Accepted class IDs must be integers from 0 through 999")
    return sorted(set(values))


def photo(con, data, title, source, version, provenance, accepted):
    if len(data)>2*1024**2:
        raise ValueError("Photo exceeds 2 MiB")
    decode(data)
    digest = sha(data)
    pid = sha(json.dumps([source,version,digest]).encode())[:32]
    con.execute("INSERT OR IGNORE INTO photos VALUES(?,?,?,?,?,?,?,?)",
                (pid,title,source,version,provenance,digest,json.dumps(labels(accepted)),data))
    return pid
