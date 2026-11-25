# BlindSpot handoff · Wednesday 25 November 2026

**The local build, tests, evidence and drafts are complete before the 17:00 WAT hard stop.** The entry materials were committed locally at 13:50 WAT in build commit `520cb65`. The new repository is `/workspace/flyio-hackathon/blindspot`, on `main`, with no remote. The author is Damien (XAVORIAN) <xavorian01@gmail.com>. Live Hacksgiving qualification requires Damien to deploy on a Sprite and verify an authenticated connector.

## What Damien can open

| Deliverable | Location under blindspot/ |
|---|---|
| Judge README, setup and real results | README.md |
| 76-second captioned local demo | evidence/walkthrough.mp4 |
| Desktop and mobile screenshots | evidence/desktop.png and evidence/mobile.png |
| Full trial data and paired images | demo/session.json, demo/followup.json and demo/images/ |
| Tests, exact commands, resource measurements and findings | TEST-RESULTS.md, evidence/pytest.txt, evidence/smoke.txt and evidence/browser.txt |
| Sprite service, checkpoint and connector instructions | DEPLOY.md and start.sh |
| Demo narration, social copy and form answers | DEMO-SCRIPT.md, SOCIAL-DRAFTS.md and FORM-DRAFT.md |
| Model pins, sample credits and project license | models/manifest.json, samples/ATTRIBUTION.md and LICENSE |

FastAPI serves a prebuilt responsive React/TypeScript console. The owner labels photos and runs bounded experiments. MobileNetV4 executes on one ONNX Runtime CPU thread. SQLite keeps image pairs, top five, probability signatures, decisions, timing, hashes and retryable memory writes. A deterministic policy promotes prior failures and escalates measured losses. The default public viewer reads bundled SAMPLE evidence. Personal photos and work-triggering endpoints require the owner token. JSON and self-contained HTML reports export locally.

The model revision is `3ba07f12712fa58fd6b3d661f9909c9e332c5005`; the 3,931,745-byte artifact has SHA-256 `270717121efb0960d60feb712574d55fa27b585f3c4afc14741d81ea980bcd9a`. The six-class main set contains twelve individually verified CC0 Cleveland Museum of Art photographs. A thirteenth distinct guitar photo is reserved for the follow-up session. The guitars were screened during development to show a measurable change. Damien can replace the museum samples with his own labelled photos through the owner UI.

## Tests and measured findings

- **27 pytest cases passed**, with one TestClient deprecation warning. Unit tests disable network connections and DNS. They cover preprocessing, exact repeatability, transforms, memory order, escalation and stopping, labels, retry/concurrency, access control, adapter errors and Box caching/partial failure.
- **Two full real-model API runs**, comprising 13 baselines and 12 variants. An independent, clean extraction of build commit `520cb65` reproduced all 25 top-five lists and scores exactly, the PNG hashes and decision reason sequences.
- **Four Chrome acceptance groups passed.** Paired images rendered on desktop, mobile selection worked at 390 px with no horizontal overflow, an authenticated run resumed after an actual Uvicorn process restart without duplicate trials, and the browser reported zero uncaught errors.
- The main set had **11 baseline errors out of 12 originals**. These led to retake requests before camera testing. On the correctly classified guitar 1918.374, blur and rotation preserved the label. Brightness ×0.65 and JPEG quality 30 changed it to Komodo dragon. Brightness ×0.35 and ×0.16 changed it to knee pad.
- On guitar 1918.370, local memory retrieved the earlier low-light failure at cosine **0.984281** and moved low light ahead of blur. The low-light prediction stayed acoustic guitar at **66.38%**. JPEG quality 12 also held. At quality 4, violin scored **93.84%**, guitar fell to **0.86%**, and the agent requested a retake.
- Across the 12 variants, **five** changed a correct baseline to a wrong top class. One crossed the project’s 70% wrong-class rule. That score is uncalibrated. The curated photographs do not establish general classifier accuracy.
- The recorded smoke took **1.529 s elapsed**, **1.461 s process CPU**, **405.730 ms inference CPU**, **123,712 KiB peak RSS** and **8,189,560 bytes** of experiment/report storage. These are local measurements. No cloud usage or price was measured.

## Verified locally and still needed to go live

The public model download, model byte/config digests, individual CC0 source records, full experiment loop, SQLite resume, in-process cosine memory, report generation, production UI and recording were verified. The required Pinecone adapter implements documented Sprites gateway paths. Unit tests exercised request bodies, redacted traces, 403/429/503, timeout, malformed replies and write retry. The optional Box adapter was exercised with simulated list, download and upload responses. The UI and logs explicitly label local operations **LOCAL/MOCK**.

1. **Fly.** Damien must inspect the existing no-card account’s remaining $1 trial credit, seven-day expiry and Sprite slots. Subject to the budget in DEPLOY.md, create `blindspot-demo` with label `blindspot`. Transfer the committed archive, install Python dependencies and pinned weights, configure owner access and register the HTTP service. Verify private URL access, cold wake and checkpoints. No Sprite, account balance, billing or platform restore was tested.
2. **Pinecone.** Create a Starter account/project with a Vectors-compatible dense `blindspot-memory` index, dimension 1000, cosine, AWS us-east-1. Store the project key in Fly’s Pinecone connector. Restrict access to the Sprite’s label and discover the exact gateway URL inside it. Select `BLINDSPOT_MEMORY=pinecone`. Verify actual upsert acknowledgement, subsequent retrieval in `blindspot-demo` and a changed test decision. A real connector round trip is pending.
3. **Optional Box.** Use a dedicated Box Individual account, consent to Fly's `root_readwrite` access, configure numeric input/output folder IDs and the actual gateway panel’s paths, then verify list, download and new-file HTML export. Personal local uploads are available immediately.
4. **Publication.** Sign into GitHub or another chosen code host later, publish the code and video, then prepare a social post and form submission. Public URLs, a published post, a live Sprite and an event submission are outstanding. No signup, OAuth, payment, push, post, message or deployment was performed in this build.

## Draft posts

## X

I built BlindSpot for @flydotio Hacksgiving. My local agent remembered a low-light failure and tested it first on another guitar. Low light passed. JPEG quality 4 turned the prediction into “violin” at 93.8%. Demo uses CC0 photos and local memory. [DEMO] [CODE]

## Bluesky

At JPEG quality 4, my inventory classifier called a guitar a violin with a 93.8% score. BlindSpot found the failure, asked for a retake, and saved the evidence. Built for @flydotio Hacksgiving. Local demo with CC0 photos and LOCAL/MOCK memory. [DEMO] [CODE]

## LinkedIn

I built BlindSpot for @flydotio Hacksgiving to answer a practical question about taking inventory photos. If a model recognizes an object on my camera, which change in lighting or image quality makes it lose the label?

In the local demo, one guitar lost its label under low light. The agent remembered the failure and tried low light first on another guitar. That photo held up. Heavy JPEG compression was the condition that changed its top prediction to violin at 93.8%, prompting a retake.

The demo uses individually credited CC0 sample photographs, local ONNX inference and durable local failure memory. The Pinecone connector path and Sprite runbook are implemented. Live connector verification is pending.

Demo [DEMO] · Code [CODE]
