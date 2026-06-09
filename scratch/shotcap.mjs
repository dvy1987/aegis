import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const URL = "https://gentle-respect-production-3704.up.railway.app/showcase";
const OUT = "scratch/shots";
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
page.on("console", (m) => console.log("PAGE:", m.type(), m.text().slice(0, 200)));
page.on("pageerror", (e) => console.log("PAGEERR:", e.message.slice(0, 200)));

await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(3500); // let hero ignition settle

// Full scroll height
const totalH = await page.evaluate(() => document.body.scrollHeight);
const vh = 900;
console.log("scrollHeight:", totalH);

// 1) Hero (top)
await page.screenshot({ path: `${OUT}/01-hero.png` });

// Step through the page in viewport-sized increments to trigger scroll reveals
let idx = 2;
for (let y = vh * 0.6; y < totalH; y += vh * 0.85) {
  await page.evaluate((yy) => window.scrollTo({ top: yy, behavior: "instant" }), y);
  await page.waitForTimeout(1400);
  const label = String(idx).padStart(2, "0");
  await page.screenshot({ path: `${OUT}/${label}-scroll-${Math.round(y)}.png` });
  idx++;
}

// Bottom
await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "instant" }));
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}/99-bottom.png` });

await browser.close();
console.log("done", idx - 1, "scroll shots");
