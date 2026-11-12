import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { delimiter, join } from 'node:path'
import puppeteer, { type Browser, type Page } from 'puppeteer-core'
import { build, preview, type PreviewServer } from 'vite'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'

// The built page with no twinky: its /ws passed to a port nothing listens on, in headless Chromium

// CHROMIUM, else Chromium or Chrome on the PATH, else the Mac's Chrome
function chromium(): string {
  const found = [
    process.env.CHROMIUM,
    ...(process.env.PATH ?? '')
      .split(delimiter)
      .flatMap((dir) => ['chromium', 'chromium-browser', 'google-chrome'].map((name) => join(dir, name))),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ].find((path) => path && existsSync(path))
  if (!found) throw new Error('No Chromium or Chrome: name one in CHROMIUM')
  return found
}

async function freePort(): Promise<number> {
  return new Promise((resolve) => {
    const server = createServer().listen(0, () => {
      const { port } = server.address() as { port: number }
      server.close(() => resolve(port))
    })
  })
}

/** The share of the page's pixels that are lit, from a screenshot. */
async function lit(page: Page): Promise<number> {
  return page.evaluate(
    async (shot: string) => {
      const image = new Image()
      image.src = `data:image/png;base64,${shot}`
      await image.decode()
      const canvas = new OffscreenCanvas(image.width, image.height)
      const context = canvas.getContext('2d')!
      context.drawImage(image, 0, 0)
      const { data } = context.getImageData(0, 0, image.width, image.height)
      let count = 0
      for (let i = 0; i < data.length; i += 4) if (data[i] + data[i + 1] + data[i + 2] > 60) count++
      return count / (data.length / 4)
    },
    await page.screenshot({ encoding: 'base64' }),
  )
}

describe('the page with no twinky', () => {
  let dist: string
  let server: PreviewServer
  let browser: Browser
  let page: Page

  beforeAll(async () => {
    dist = mkdtempSync(join(tmpdir(), 'twinky-dist-'))
    await build({ logLevel: 'silent', build: { outDir: dist, emptyOutDir: true } })
    const nothing = await freePort()
    server = await preview({
      logLevel: 'silent',
      build: { outDir: dist },
      preview: { port: await freePort(), proxy: { '/ws': { target: `ws://localhost:${nothing}`, ws: true } } },
    })
    browser = await puppeteer.launch({
      executablePath: chromium(),
      args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
    })
    page = await browser.newPage()
    await page.setViewport({ width: 1280, height: 800 })
    await page.goto(server.resolvedUrls!.local[0])
  }, 120_000)

  afterAll(async () => {
    await browser?.close()
    await server?.close()
    rmSync(dist, { recursive: true, force: true })
  })

  it('simulates the tree, says so, and draws it', { timeout: 60_000 }, async () => {
    await page.waitForSelector('select[aria-label="Pattern"]', { timeout: 50_000 })
    expect(await page.$eval('header .status', (s) => s.textContent)).toContain(
      'Simulated tree: no twinky.py answered. Run twinky.py to play your tree live.',
    )
    expect(await page.$eval('.listen', (s) => s.textContent)).toContain('needs twinky.py')
    await new Promise((resolve) => setTimeout(resolve, 1000))
    expect(await lit(page)).toBeGreaterThan(0.002)
  })

  it('switches patterns from the picker', { timeout: 60_000 }, async () => {
    const pattern = 'select[aria-label="Pattern"]'
    const fireworks = await page.$eval(pattern, (s) =>
      [...(s as HTMLSelectElement).options].findIndex((o) => o.text === 'Fireworks'),
    )
    expect(fireworks).toBeGreaterThan(0)
    await page.select(pattern, String(fireworks))
    await page.waitForFunction(() => document.querySelector('.simulated .to')?.textContent === 'changing to Fireworks')
    // a change lasts 6 seconds
    await page.waitForFunction(
      (selector: string) => {
        const s = document.querySelector(selector) as HTMLSelectElement
        return s.options[s.selectedIndex].text === 'Fireworks' && !document.querySelector('.simulated .to')
      },
      { timeout: 20_000 },
      pattern,
    )
    expect(await page.$$eval('.simulated legend', (ls) => ls.map((l) => l.textContent))).toContain('Fireworks')
  })
})
