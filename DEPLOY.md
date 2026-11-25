# Run BlindSpot on one Sprite

**Status on November 25, 2026.** Local inference, bounded runs, process restart and local cosine retrieval are tested. Fly account state, live provider access, service registration, cold wake and checkpoints await Damien’s verification. All commands below are instructions for a future authorized session. No provider secret belongs in the repository, environment file or Python process.

## Accounts and budget

1. In the existing Fly dashboard inspect remaining credit, expiry and available Sprite slots. The no-card plan begins with one $1 credit expiring after seven days and allows up to three Sprites. Use one Sprite. Limit incremental use to the smaller of $0.50 or the remaining balance above a $0.25 reserve. If there is no room, use the local recording. [Fly plan](https://docs.fly.io/about/free-plan)
2. Create a no-card Pinecone Starter project. Set up a dense, Vectors-compatible index named `blindspot-memory`, dimension **1000**, metric **cosine**, in the Starter-supported AWS us-east-1 region. Supply your own vectors. Confirm the available index type supports the legacy query/upsert operations exposed by Fly. Create a project key with the required index discovery, query and upsert permissions. Store it in the Fly organization’s Pinecone connector. [Pinecone vector setup](https://docs.pinecone.io/guides/legacy/vectors-api/create-a-vector-index) · [Fly Pinecone catalog](https://fly.io/sprites/ecosystem/#connectors/pinecone)
3. In Fly → Sprites → Connectors, disable allow-all, grant the `blindspot` label and check the authorized Sprite after creation. The gateway attaches identity. An ordinary internet client does not exercise this path. [Gateway documentation](https://docs.fly.io/sprites/concepts/connectors)
4. Optional Box requires a separate free Individual account, two folders and consent to Fly’s account-wide `root_readwrite` scope. Use a dedicated demo account. GitHub sign-in is needed later only if Damien chooses GitHub for code publication. Publishing a demo, social post and form submission are separate owner actions. [Box catalog](https://fly.io/sprites/ecosystem/#connectors/box)

## Create and install

The CLI reference documents the create label flag, named Sprite selection, file upload with exec, and console syntax. The archive transfer and installation below are project-specific recipes, unverified on a Sprite. Use an authenticated owner terminal later. [Sprite CLI](https://docs.fly.io/sprites/cli/commands)

```bash
sprite create blindspot-demo --label blindspot --skip-console
mkdir -p .local
git archive --format=tar.gz --output=.local/blindspot.tar.gz HEAD
sprite exec -s blindspot-demo --file .local/blindspot.tar.gz:/tmp/blindspot.tar.gz -- sh -c 'mkdir -p /home/sprite/blindspot && tar xzf /tmp/blindspot.tar.gz -C /home/sprite/blindspot'
sprite console -s blindspot-demo
```

Inside the Sprite, verify Python 3.13 availability. That is the interpreter used for the locked local build. Install assets once on persistent disk. The archive contains prebuilt frontend assets. The public model installer checks the pinned digests.

```bash
cd /home/sprite/blindspot
python3.13 -m venv .local/venv
.local/venv/bin/python -m pip install -r requirements.txt
.local/venv/bin/python scripts/fetch_model.py
.local/venv/bin/python scripts/smoke.py --data .local/install-smoke
curl -fsS https://api.sprites.dev/v1/gateway/list
```

The discovery request is documented for use inside the Sprite. Copy the exact Pinecone base URL from the response or the connector detail page. The install smoke intentionally forces LOCAL/MOCK.

## Private owner configuration

Create `.local/service.env` with mode 600. Use shell-quoted values. The example’s base URL must be replaced with the actual org connection URL. The owner token is an application access secret chosen by Damien. An interactive read avoids leaving it in shell history.

```bash
umask 077
cat > .local/service.env <<'ENV'
HOST=0.0.0.0
PORT=8080
BLINDSPOT_MODE=owner
BLINDSPOT_MEMORY=pinecone
BLINDSPOT_PINECONE_URL=https://api.sprites.dev/v1/gateway/pinecone/REPLACE_WITH_CONNECTION_ID
BLINDSPOT_INDEX=blindspot-memory
BLINDSPOT_BOX=0
ENV
read -rsp 'Choose the BlindSpot owner token: ' owner_token
echo
printf 'BLINDSPOT_OWNER_TOKEN=%q\n' "$owner_token" >> .local/service.env
unset owner_token
```

`BLINDSPOT_DATA` optionally changes the persistent directory, defaulting to `data/` under the project. `BLINDSPOT_PYTHON` optionally overrides the executable. `BLINDSPOT_MEMORY=local` selects SQLite-backed LOCAL/MOCK. `BLINDSPOT_MODE=demo` exposes only packaged sample evidence regardless of an owner token. Keep Fly URL authentication at its private default during validation.

## Service, connector proof and recovery

The following in-Sprite command uses the documented service options. The project-specific absolute script, directory and HTTP port have been checked against the local layout. Service registration on Fly remains untested. [Service reference](https://docs.fly.io/sprites/concepts/services)

```bash
sprite-env services create blindspot --cmd /home/sprite/blindspot/start.sh --dir /home/sprite/blindspot --http-port 8080
sprite-env services get blindspot
curl -fsS http://127.0.0.1:8080/api/status
```

Use the private owner UI to run the 12-photo sample, then the follow-up. The first correct guitar baseline queries memory. Its first induced failure sends one 1,000-value normalized vector. The second session should return the same evidence ID if indexing is visible. Inspect the real provider, method, HTTP status, timing and retrieved case. Stable identifiers are `run_id:photo_id` in namespace `blindspot-demo`.

| Operation | Documented gateway suffix | Acceptance |
|---|---|---|
| Upsert | `/indexes/blindspot-memory/vectors/upsert` | 2xx and `upsertedCount: 1`, no pending write |
| Query | `/indexes/blindspot-memory/query` | Same model/owner filter, up to three hits, earlier condition and evidence ID returned |

A 429 or network error is visible in the trace. Use **Retry pending memory write** once after the provider recovers. If a completed upsert takes time to index, wait briefly and start one new follow-up run. A 2xx with an empty match set leaves the default order intact. A live upsert, subsequent retrieval and changed order are the qualification gate. The app supplies no auth header to the gateway. [Pinecone connector](https://fly.io/sprites/ecosystem/#connectors/pinecone)

After validating install and finishing outstanding writes/exports, make a checkpoint. The following forms are documented. Substitute the ID actually returned for `v4` if a later restore is deliberately authorized. Restore restarts the environment and replaces disk state. Pinecone and Box retain their independent history. [Checkpoint reference](https://docs.fly.io/sprites/concepts/checkpoints)

```bash
sprite-env checkpoints create --comment "BlindSpot verified install"
sprite-env checkpoints list
sprite-env checkpoints create --comment "Before preprocessing experiment"
# Example only, inside the Sprite, for an intentional rollback
sprite-env checkpoints restore v4
```

To verify wake behavior, leave a run between steps, record its ID and cursor, close console sessions and leave the app idle. Reopen it after a verified pause, select the run and continue. Check trial IDs and the service state. Record the type of wake only if platform evidence establishes it. Local process-restart evidence is in the test results. For any later public demo, switch the application to demo mode, restart the service, verify owner actions get 403, then make a separate decision about public URL access. [Lifecycle](https://docs.fly.io/sprites/concepts/lifecycle) · [Networking](https://docs.fly.io/sprites/concepts/networking)

## Optional Box intake and export

Enable `BLINDSPOT_BOX=1`. Set `BLINDSPOT_BOX_URL` to Fly’s exact Box connection base and set `BLINDSPOT_BOX_INPUT` and `BLINDSPOT_BOX_OUTPUT` to numeric folder IDs. Copy the gateway suffixes for listing, download and multipart upload from the connection’s **API Usage** panel into `BLINDSPOT_BOX_LIST_PATH`, `BLINDSPOT_BOX_DOWNLOAD_PATH` and `BLINDSPOT_BOX_UPLOAD_PATH`. In the first two templates replace the numeric folder/file ID with literal `{folder}` or `{file}`. The public catalog confirms capabilities and limits but does not publish the org panel’s exact paths or download response behavior. The adapter expects gateway-served bytes and declines redirects. Confirm each path with the dedicated account before enabling it. [Box connector](https://fly.io/sprites/ecosystem/#connectors/box)

Upload 1–12 owned files and a `labels.json` list such as `[{"file":"my-guitar.jpg","accepted":[402]}]`. Use **Import Box folder**. Verify source ID, version, hash and a real gateway GET in the run trace. After a run choose **Export to Box**, confirm the new HTML file in the output folder and open it. Local upload and local JSON/HTML export remain available.

## Keep the trial small

Use the prebuilt UI, one worker, one inference thread, one compact model and explicit continuation. Close idle consoles. No polling, background inference, external database server or managed model service is required. Monitor the dashboard after each session. Published rates include $0.0385/CPU-hour, $0.021875/GB-hour RAM, $0.000683/hot GB-hour and $0.000027/cold GB-hour. Storage can accrue during sleep. A planning example of six CPU-hours, 1.5 RAM GB-hours, three hot GB-hours and 60 cold GB-hours is about $0.267 before other charges. The local resource measurements do not predict a Fly invoice. [Pricing](https://fly.io/pricing/)
