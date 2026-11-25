import json
import sqlite3

import numpy as np
import PIL

from . import connectors as mem
from .store import uid
from .vision import CONDITIONS, MODEL, PRE, decode, png, predict, sha, transform

MILD = ("blur", "low light", "JPEG")
EXTRA = ("rotation", "occlusion", "colour cast", "glare")


def create(con, ids, seed, budget, goal):
    if (
        not 1 <= len(ids) <= 12
        or len(set(ids)) != len(ids or [])
        or not 1 <= budget <= 72
    ):
        raise ValueError("Select 1–12 distinct photos and a budget of 1–72 variants")
    photos = [lookup(con, "photos", i) for i in ids]
    run = uid()
    try:
        con.execute(
            "INSERT INTO runs(id,goal,model_sha,preprocessing_sha,state,seed,budget) VALUES(?,?,?,?,?,?,?)",
            (run, goal, MODEL, PRE, "active", seed, budget),
        )
    except sqlite3.IntegrityError:
        raise ValueError("Continue the active run first") from None
    con.executemany(
        "INSERT INTO cases(run_id,photo_id,position,labels) VALUES(?,?,?,?)",
        [(run, p["id"], i, p["accepted"]) for i, p in enumerate(photos)],
    )
    con.execute(
        """INSERT INTO run_intakes SELECT DISTINCT cases.run_id,photo_intakes.batch
                 FROM cases JOIN photo_intakes USING(photo_id) WHERE cases.run_id=?""",
        (run,),
    )
    return run


def lookup(con, table, id):
    row = con.execute(f"SELECT * FROM {table} WHERE id=?", (id,)).fetchone()
    if row is None:
        raise KeyError(id)
    return row


def next_test(previous, recall, seed, baseline_mass=1.0):
    preferred = next(
        (
            h
            for h in recall
            if h["score"] >= 0.15 and h["metadata"].get("condition") in CONDITIONS
        ),
        None,
    )
    order = list(MILD) + [EXTRA[seed % 4]]
    if preferred:
        first = preferred["metadata"]["condition"]
        order = [first] + [x for x in order if x != first]
    for condition in order:
        if all(t["condition"] != condition for t in previous):
            changed = not previous and preferred and condition != MILD[0]
            return (
                condition,
                1,
                "RECALLED_FAILURE" if changed else "MILD_PROBE",
                ([preferred["id"]] if changed else []),
            )
    # Compare approved-label probability mass with the common baseline.
    # Smallest mass corresponds to the largest reduction.
    mild = [t for t in previous if t["level"] == 1]
    best = min(mild, key=lambda t: t["mass"])
    if best["mass"] >= baseline_mass:
        return None, 0, "NO_LABEL_DROP", [t["id"] for t in mild]
    level = max(t["level"] for t in previous if t["condition"] == best["condition"]) + 1
    return best["condition"], level, "LARGEST_LABEL_DROP", [best["id"]]


def trial(con, run, photo, accepted, condition, level):
    seed = run["seed"] if condition == "occlusion" else 0
    spec = json.dumps(
        dict(
            condition=condition,
            level=level,
            seed=seed,
            pipeline="rgb768-v1",
            pillow=PIL.__version__,
        ),
        sort_keys=True,
    )
    key = sha(json.dumps([MODEL, PRE, photo["sha256"], spec]).encode())
    art = con.execute("SELECT * FROM artifacts WHERE id=?", (key,)).fetchone()
    cached = art is not None
    if not cached:
        image = decode(photo["original"])
        if level:
            image = transform(image, condition, level, seed)
        probs, top, ms = predict(image)
        data = png(image)
        con.execute(
            "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)",
            (key, spec, json.dumps(top), probs.tobytes(), ms, sha(data), data),
        )
        art = lookup(con, "artifacts", key)
    probs = np.frombuffer(art["probs"], np.float32)
    score = float(probs[accepted].sum())
    top_id = int(probs.argmax())
    if top_id in accepted:
        outcome = "accepted"
    elif not level:
        outcome = "baseline error"
    else:
        outcome = "confident error" if probs[top_id] >= 0.70 else "induced error"
    tid = uid()
    con.execute(
        "INSERT INTO trials VALUES(?,?,?,?,?,?,?,?,?)",
        (tid, run["id"], photo["id"], key, condition, level, score, outcome, cached),
    )
    return tid, probs, outcome


def pending(con, run, photo):
    return con.execute(
        "SELECT * FROM outbox WHERE run_id=? AND photo_id=?", (run, photo)
    ).fetchone()


def step(con, rid, expected):
    run = lookup(con, "runs", rid)
    if run["state"] != "active" or expected != run["cursor"]:
        return
    queued = None
    case = con.execute(
        "SELECT * FROM cases WHERE run_id=? AND state NOT IN ('done','retake') ORDER BY position LIMIT 1",
        (rid,),
    ).fetchone()
    pid = case["photo_id"]
    photo = lookup(con, "photos", pid)
    remaining = (
        run["budget"]
        - con.execute(
            "SELECT count(*) FROM trials WHERE run_id=? AND level>0", (rid,)
        ).fetchone()[0]
    )

    def decide(action, reason, evidence):
        con.execute(
            "INSERT INTO decisions VALUES(?,?,?,?,?,?)",
            (rid, pid, action, reason, json.dumps(evidence), remaining),
        )

    def state(new):
        con.execute(
            "UPDATE cases SET state=? WHERE run_id=? AND photo_id=?", (new, rid, pid)
        )

    accepted = json.loads(case["labels"])
    previous = list(
        con.execute(
            "SELECT * FROM trials WHERE run_id=? AND photo_id=? ORDER BY rowid",
            (rid, pid),
        )
    )
    if not accepted:
        if case["state"] == "label":
            return
        decide("ASK_LABEL", "MISSING_CLASS_IDS", [pid])
        state("label")
    elif not previous:
        tid, probs, outcome = trial(con, run, photo, accepted, "original", 0)
        decide("TEST", "BASELINE", [tid])
        if outcome == "baseline error":
            decide("REQUEST_RETAKE", "BASELINE_DISAGREES", [tid])
            state("retake")
        else:
            try:
                hits = mem.recall(con, rid, mem.signature(probs))
            except mem.Unavailable:
                hits = []
                decide("TEST", "REMOTE_MEMORY_UNAVAILABLE", [tid])
            con.execute(
                "UPDATE cases SET recall=?,state='testing' WHERE run_id=? AND photo_id=?",
                (json.dumps(hits), rid, pid),
            )
    elif remaining == 0:
        decide("STOP", "SESSION_BUDGET", [])
        state("done")
    else:
        condition, level, reason, ids = next_test(
            previous[1:],
            json.loads(case["recall"]),
            run["seed"] + case["position"],
            previous[0]["mass"],
        )
        if condition is None:
            decide("STOP", reason, ids)
            state("done")
        else:
            tid, _, outcome = trial(con, run, photo, accepted, condition, level)
            remaining -= 1
            decide("TEST", reason, [*ids, tid])
            if outcome != "accepted" and not pending(con, rid, pid):
                base = lookup(con, "artifacts", previous[0]["artifact"])
                vector = mem.signature(np.frombuffer(base["probs"], np.float32))
                item = dict(
                    id=f"{rid}:{pid}",
                    values=vector.tolist(),
                    metadata=dict(
                        model=MODEL,
                        owner=mem.OWNER,
                        condition=condition,
                        trial=tid,
                        accepted=[str(i) for i in accepted],
                        outcome=outcome,
                    ),
                )
                con.execute(
                    "INSERT INTO outbox VALUES(?,?,?,?,?,?)",
                    (item["id"], rid, pid, mem.provider(), json.dumps(item), "pending"),
                )
                queued = item["id"]
            if outcome == "confident error":
                decide("REQUEST_RETAKE", "WRONG_TOP1_GE_070", [tid])
                state("retake")
            elif len(previous) >= 6 or remaining == 0:
                decide(
                    "STOP",
                    "PHOTO_LIMIT" if len(previous) >= 6 else "SESSION_BUDGET",
                    [tid],
                )
                state("done")

    active = con.execute(
        "SELECT 1 FROM cases WHERE run_id=? AND state NOT IN ('done','retake')", (rid,)
    ).fetchone()
    con.execute(
        "UPDATE runs SET cursor=cursor+1,state=? WHERE id=?",
        ("active" if active else "done", rid),
    )
    return queued


def relabel(con, pid, accepted):
    lookup(con, "photos", pid)
    value = json.dumps(accepted)
    con.execute("UPDATE photos SET accepted=? WHERE id=?", (value, pid))
    con.execute(
        """UPDATE cases SET labels=?,state='new' WHERE photo_id=? AND state IN ('label','new')
                   AND run_id IN (SELECT id FROM runs WHERE state='active')""",
        (value, pid),
    )
