import { chromium } from "playwright"
import { mkdir } from "node:fs/promises"
import { fileURLToPath } from "node:url"

const BASE = "http://localhost:5178"
const OUT = fileURLToPath(new URL("../screenshots/", import.meta.url))

const shots = [
  { name: "01-login", path: "/login", width: 1440, height: 900 },
  {
    name: "02-learn-chat",
    path: "/learn/s-tcp-handshake",
    width: 1440,
    height: 900,
  },
  {
    name: "03-learn-questions",
    path: "/learn/s-tcp-handshake?panel=questions",
    width: 1440,
    height: 900,
  },
  {
    name: "04-question-detail",
    path: "/learn/s-tcp-handshake?panel=questions&question=q-why-three",
    width: 1440,
    height: 900,
  },
  {
    name: "05-memory",
    path: "/learn/s-tcp-handshake?panel=memory",
    width: 1440,
    height: 900,
  },
  { name: "06-lab-chat", path: "/lab/s-tcpdump", width: 1440, height: 900 },
  {
    name: "07-sandbox",
    path: "/lab/s-tcpdump?panel=sandbox",
    width: 1440,
    height: 900,
  },
  { name: "08-styleguide", path: "/styleguide", width: 1440, height: 900, full: true },
  { name: "09-mobile-login", path: "/login", width: 390, height: 844, mobile: true },
  {
    name: "10-mobile-chat",
    path: "/learn/s-tcp-handshake",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "11-mobile-questions",
    path: "/learn/s-tcp-handshake?panel=questions",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "12-mobile-memory",
    path: "/learn/s-tcp-handshake?panel=memory",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "13-mobile-memory-file",
    path: "/learn/s-tcp-handshake?panel=memory&path=/memory/profile.md",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "14-mobile-sandbox",
    path: "/lab/s-tcpdump?panel=sandbox",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "15-mobile-rail",
    path: "/learn/s-tcp-handshake",
    width: 390,
    height: 844,
    mobile: true,
    action: "rail",
  },
  {
    name: "16-mobile-editor",
    path: "/learn/s-tcp-handshake?panel=questions",
    width: 390,
    height: 844,
    mobile: true,
    action: "editor",
  },
  {
    name: "17-tablet-chat",
    path: "/learn/s-tcp-handshake",
    width: 1024,
    height: 768,
  },
  {
    name: "18-checkpoint-answered",
    path: "/learn/s-tcp-handshake",
    width: 1440,
    height: 900,
    action: "answer",
  },
  {
    name: "19-sandbox-stopped",
    path: "/lab/s-tcpdump?panel=sandbox",
    width: 1440,
    height: 900,
    action: "destroy",
  },
  {
    name: "20-empty-chat",
    path: "/learn/s-tcp-handshake",
    width: 1440,
    height: 900,
    action: "new-session",
  },
  {
    name: "21-question-editor",
    path: "/learn/s-tcp-handshake?panel=questions",
    width: 1440,
    height: 900,
    action: "editor",
  },
  {
    name: "22-question-revealed",
    path: "/learn/s-tcp-handshake?panel=questions&question=q-why-three",
    width: 1440,
    height: 900,
    action: "reveal",
  },
  {
    name: "23-mobile-question-detail",
    path: "/learn/s-tcp-handshake?panel=questions&question=q-why-three",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "24-mobile-styleguide",
    path: "/styleguide",
    width: 390,
    height: 844,
    mobile: true,
  },
  {
    name: "25-sidebar-collapsed",
    path: "/learn/s-tcp-handshake",
    width: 1440,
    height: 900,
    action: "collapse",
  },
]

await mkdir(OUT, { recursive: true })

const browser = await chromium.launch()
const errors = []

for (const shot of shots) {
  const context = await browser.newContext({
    viewport: { width: shot.width, height: shot.height },
    deviceScaleFactor: 1,
    isMobile: Boolean(shot.mobile),
    hasTouch: Boolean(shot.mobile),
  })
  const page = await context.newPage()
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(`[${shot.name}] console: ${message.text()}`)
    }
  })
  page.on("pageerror", (error) => {
    errors.push(`[${shot.name}] pageerror: ${error.message}`)
  })

  await page.goto(`${BASE}${shot.path}`, { waitUntil: "networkidle" })
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(450)

  if (shot.action === "rail") {
    await page.getByRole("button", { name: "打开会话列表" }).click()
    await page.waitForTimeout(350)
  }

  if (shot.action === "answer") {
    await page.getByRole("radio", { name: /B\. 停留在 SYN_SENT/ }).click()
    await page.getByRole("button", { name: "提交作答" }).click()
    await page.waitForTimeout(1500)
  }

  if (shot.action === "editor") {
    await page.getByRole("button", { name: "新建私有题" }).click()
    await page.waitForTimeout(400)
  }

  if (shot.action === "reveal") {
    await page.getByRole("button", { name: "查看答案" }).click()
    await page.waitForTimeout(300)
  }

  if (shot.action === "destroy") {
    await page.getByRole("button", { name: "销毁", exact: true }).click()
    await page.waitForTimeout(300)
    await page.getByRole("button", { name: "销毁沙盒" }).click()
    await page.waitForTimeout(1400)
  }

  if (shot.action === "new-session") {
    await page.getByRole("button", { name: "新建会话" }).first().click()
    await page.waitForTimeout(600)
  }

  if (shot.action === "collapse") {
    await page.getByRole("button", { name: "收起侧栏" }).click()
    await page.waitForTimeout(450)
  }

  const overflow = await page.evaluate(() => ({
    doc: document.documentElement.scrollWidth - window.innerWidth,
    body: document.body.scrollWidth - window.innerWidth,
    inner: window.innerWidth,
    visual: window.visualViewport?.width ?? window.innerWidth,
  }))
  if (overflow.doc > 1 || overflow.body > 1) {
    errors.push(
      `[${shot.name}] overflow doc=${overflow.doc} body=${overflow.body} inner=${overflow.inner} visual=${overflow.visual}`,
    )
  }
  if (shot.mobile && Math.abs(overflow.inner - shot.width) > 2) {
    errors.push(
      `[${shot.name}] mobile layout viewport expanded: ${overflow.inner} vs ${shot.width}`,
    )
  }

  await page.screenshot({
    path: `${OUT}/${shot.name}.png`,
    fullPage: Boolean(shot.full),
  })
  await context.close()
}

await browser.close()

if (errors.length) {
  console.log("ISSUES:\n" + errors.join("\n"))
} else {
  console.log("No console errors or horizontal overflow.")
}
