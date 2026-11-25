// Render a captioned walkthrough of the two immutable local SAMPLE replays.
import { spawn, execFileSync } from "node:child_process";
import { mkdtemp, writeFile, mkdir } from "node:fs/promises";
import { once } from "node:events";
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";
const root = fileURLToPath(new URL("../", import.meta.url));
const work = await mkdtemp(path.join(root, ".local/tmp/record-"));
const server = spawn("./start.sh", [], {
  cwd: root,
  env: {
    ...process.env,
    HOST: "127.0.0.1",
    PORT: "18480",
    BLINDSPOT_MODE: "demo",
  },
  stdio: ["ignore", "ignore", "pipe"],
});
let browser;
try {
  let log = "";
  server.stderr.on("data", (b) => (log += b));
  for (let n = 0; n < 100 && !log.includes("Uvicorn running on"); n++) {
    if (server.exitCode !== null) throw Error(log);
    await new Promise((r) => setTimeout(r, 100));
  }
  if (!log.includes("Uvicorn running on")) throw Error("Server startup failed");
  browser = await puppeteer.launch({
    executablePath: process.env.CHROME_BIN || "/usr/bin/google-chrome",
    headless: true,
    userDataDir: path.join(work, "profile"),
    env: {
      ...process.env,
      TMPDIR: work,
      XDG_CONFIG_HOME: work,
      XDG_CACHE_HOME: work,
      CHROME_CONFIG_HOME: work,
    },
    args: [
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--disable-background-networking",
      "--disable-component-update",
      "--disable-breakpad",
      "--disable-crashpad",
      "--disable-sync",
      "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1",
    ],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto("http://127.0.0.1:18480", { waitUntil: "networkidle0" });
  const shots = [
    [
      "session",
      0,
      "top",
      10,
      "BlindSpot tests a classifier against labels I supply. This saved local run uses 12 CC0 museum photos. Eleven already missed at baseline.",
    ],
    [
      "session",
      1,
      "pair",
      9,
      "On this guitar, the original scores 65.1% for acoustic guitar. Mild blur keeps the label and raises its score to 89.4%.",
    ],
    [
      "session",
      2,
      "pair",
      11,
      "Lowering brightness to 65% switches the top class to Komodo dragon. The accepted guitar score falls to 5.1%. BlindSpot remembers this failure.",
    ],
    [
      "followup",
      1,
      "memory",
      12,
      "A different guitar retrieves the earlier failure at cosine similarity 0.984. Local memory moves low light ahead of blur. There is no generative planner.",
    ],
    [
      "followup",
      1,
      "pair",
      10,
      "Low light keeps the new guitar classified correctly. The prior failure changed which experiment ran first. It did not predict the result.",
    ],
    [
      "followup",
      6,
      "pair",
      12,
      "At JPEG quality 4, violin takes the lead at 93.8%. That crosses the agent’s 70% wrong-class threshold and triggers a retake request.",
    ],
    [
      "followup",
      6,
      "report",
      12,
      "The report preserves predictions, hashes and CPU time. These traces use LOCAL/MOCK. The Sprite and live Pinecone connection still need verification.",
    ],
  ];
  let current = "";
  const list = [];
  for (const [i, [session, trial, area, seconds, caption]] of shots.entries()) {
    if (session !== current) {
      const name =
        session === "session" ? "Sample collection" : "Follow-up session";
      await page.evaluate(
        (name) =>
          [...document.querySelectorAll("button.nav")]
            .find((b) => b.textContent.startsWith(name))
            .click(),
        name,
      );
      await page.waitForFunction(
        (n) => document.querySelector("h1")?.textContent === n,
        {},
        name,
      );
      current = session;
    }
    await page.waitForFunction(
      (i) => document.querySelectorAll(".tabs button").length > i,
      {},
      trial,
    );
    await page.evaluate(
      (i) => document.querySelectorAll(".tabs button")[i].click(),
      trial,
    );
    await page.waitForFunction(
      (i) =>
        document
          .querySelectorAll(".tabs button")
          [i]?.getAttribute("aria-pressed") === "true",
      {},
      trial,
    );
    await page.waitForFunction(() =>
      Array.from(document.querySelectorAll(".pair img")).every(
        (im) => im.complete && im.naturalWidth > 0,
      ),
    );
    await page.evaluate(
      ({ area, caption }) => {
        if (area === "top") scrollTo(0, 0);
        else
          document
            .querySelector(
              area === "pair"
                ? ".pair"
                : area === "memory"
                  ? ".detailsgrid"
                  : "dl",
            )
            .scrollIntoView({ block: area === "report" ? "end" : "start" });
        let bar = document.querySelector("#caption");
        if (!bar) {
          bar = document.createElement("div");
          bar.id = "caption";
          bar.style.cssText =
            "position:fixed;bottom:0;left:0;right:0;z-index:100;background:#0b100df7;border-top:2px solid #c6f889;padding:16px 42px;color:#f8fff4;font-size:22px;line-height:1.4";
          document.body.appendChild(bar);
        }
        bar.textContent = caption;
      },
      { area, caption },
    );
    const shot = path.join(work, "frame" + i + ".png");
    await page.screenshot({ path: shot });
    list.push("file '" + shot + "'", "duration " + seconds);
  }
  list.push(list[list.length - 2]);
  const input = path.join(work, "frames.txt");
  await writeFile(input, list.join("\n") + "\n");
  await mkdir(path.join(root, "evidence"), { recursive: true });
  execFileSync("ffmpeg", [
    "-hide_banner",
    "-loglevel",
    "error",
    "-y",
    "-f",
    "concat",
    "-safe",
    "0",
    "-i",
    input,
    "-vf",
    "fps=10,format=yuv420p",
    "-c:v",
    "libx264",
    "-t",
    "76",
    "-threads",
    "2",
    "-crf",
    "20",
    "-movflags",
    "+faststart",
    path.join(root, "evidence/walkthrough.mp4"),
  ]);
  console.log("Rendered 7 captioned views of saved local experiments.");
} finally {
  if (browser) await browser.close();
  if (server.exitCode === null) {
    const closed = once(server, "exit");
    server.kill();
    await closed;
  }
}
