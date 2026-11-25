# BlindSpot · 76-second walkthrough

[Play the local captioned walkthrough](evidence/walkthrough.mp4). The clip presents seven views of measured, saved SAMPLE runs. The following lines can also be spoken during a local demonstration.

| Time | Screen | Narration |
|---|---|---|
| 0–10 s | Sample collection, original guitar | “BlindSpot tests a classifier against labels I supply. Here I’m using twelve CC0 museum photos. Eleven already missed at baseline, so the agent asks for retakes before testing camera conditions.” |
| 10–19 s | Guitar 1918.374, original and mild blur | “This guitar starts correctly at 65%. Mild blur actually raises the guitar score to 89%. That test passes.” |
| 19–30 s | Low light, level 1 | “At 65% brightness, the top class changes to Komodo dragon. The accepted guitar score falls to 5%. BlindSpot records the condition and the original model response.” |
| 30–42 s | Follow-up, failure memory and trace | “I give it a different guitar. Local memory retrieves the first failure at cosine similarity 0.984. Low light now comes before blur. A bounded policy makes that choice without a generative planner.” |
| 42–52 s | Follow-up, low light | “This time low light preserves the guitar label. The earlier failure earned a test. The new photo still gets its own measurement.” |
| 52–64 s | Follow-up, JPEG level 3 | “JPEG causes the largest mild loss, so BlindSpot increases compression. At quality four, violin wins at 93.8%. That crosses the wrong-class threshold. The agent asks for a clearer photo.” |
| 64–76 s | Decision timeline and report | “The report saves the images, top five, hashes and CPU time. These traces say LOCAL/MOCK. The Pinecone gateway adapter and Sprite runbook are ready for Damien’s live verification.” |

For a live local take, use **Owner workspace → Load 12 samples → Create run → Continue experiment**, then repeat with **Load follow-up**. Use a new local data directory for the two-session sequence. Show the results that actually appear. The recording uses captioned browser frames and contains no audio. Describe a Sprite cold wake, remote retrieval or Box export only after verifying that event in the live environment. The Chrome test separately verified a local server restart.

To regenerate the local recording after building the UI, run `node web/record.mjs`. It requires local Chrome, the frontend development dependencies and FFmpeg with H.264 encoding.
