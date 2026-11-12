import { existsSync } from 'node:fs'
import { delimiter, join } from 'node:path'
import react from '@vitejs/plugin-react'
import puppeteer, { type Browser, type Page } from 'puppeteer-core'
import { createServer, type Plugin, type ViteDevServer } from 'vite'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'

// The Listen panel alone, from the dev server, in headless Chromium, its tab shared by a stubbed
// getDisplayMedia: a canvas's video, with an 80 Hz tone's audio unless the page says none

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

/** /listen.html, the panel with what it sends kept in window.sent. */
function listenPage(): Plugin {
  const entry = '\0listen-entry.js'
  return {
    name: 'listen-page',
    resolveId: (source) => (source === '/listen-entry.js' ? entry : undefined),
    load: (id) =>
      id === entry
        ? `import { createElement } from 'react'
           import { createRoot } from 'react-dom/client'
           import Listen from '/src/Listen.tsx'
           import '/src/app.css'
           window.sent = []
           createRoot(document.getElementById('root')).render(
             createElement(Listen, { send: (message) => window.sent.push(JSON.parse(message).music) }),
           )`
        : undefined,
    configureServer(server) {
      server.middlewares.use('/listen.html', (_, response) => {
        const html = '<!doctype html><div id="root"></div><script type="module" src="/listen-entry.js"></script>'
        void server.transformIndexHtml('/listen.html', html).then((page) => {
          response.setHeader('Content-Type', 'text/html')
          response.end(page)
        })
      })
    },
  }
}

declare global {
  interface Window {
    sent: { low: number }[]
    asked: DisplayMediaStreamOptions
    shared: MediaStream
    tabAudio: boolean
  }
}

/** The stubbed share, on every load. */
function stubShare() {
  window.tabAudio = true
  navigator.mediaDevices.getDisplayMedia = async (options) => {
    window.asked = options!
    const canvas = document.createElement('canvas')
    const tracks: MediaStreamTrack[] = canvas.captureStream().getVideoTracks()
    if (window.tabAudio) {
      const context = new AudioContext()
      const tone = context.createOscillator()
      const out = context.createMediaStreamDestination()
      tone.frequency.value = 80
      tone.connect(out)
      tone.start()
      tracks.push(...out.stream.getAudioTracks())
    }
    window.shared = new MediaStream(tracks)
    return window.shared
  }
}

const error = (page: Page) => page.$eval('.listen', (s) => s.querySelector('.error')?.textContent ?? null)
const low = (page: Page) =>
  page.$eval('.listen .meter > div > div', (bar) => parseFloat((bar as HTMLElement).style.width))

describe('listening to a tab', () => {
  let server: ViteDevServer
  let browser: Browser
  let page: Page

  beforeAll(async () => {
    server = await createServer({
      configFile: false,
      root: 'web',
      logLevel: 'silent',
      plugins: [react(), listenPage()],
      server: { port: 0 },
    })
    await server.listen()
    browser = await puppeteer.launch({
      executablePath: chromium(),
      args: ['--no-sandbox', '--autoplay-policy=no-user-gesture-required'],
    })
  }, 60_000)

  afterAll(async () => {
    await browser?.close()
    await server?.close()
  })

  /** A fresh panel, with the tab's audio shared or not, after Listen to a tab. */
  async function share(audio: boolean) {
    page = await browser.newPage()
    await page.evaluateOnNewDocument(stubShare)
    await page.goto(new URL('listen.html', server.resolvedUrls!.local[0]).href)
    await page.evaluate((audio: boolean) => (window.tabAudio = audio), audio)
    const tab = await page.waitForSelector('xpath/.//button[text()="Listen to a tab"]', { timeout: 30_000 })
    await tab!.click()
    await page.waitForSelector('select[aria-label="Input"]')
  }

  it('feeds the analyser the tab audio alone, the video stopped', { timeout: 60_000 }, async () => {
    await share(true)
    await page.waitForFunction(() => window.sent.some((m) => m.low > 0.5), { timeout: 20_000 })
    expect(await page.evaluate(() => window.asked)).toEqual({ audio: true, video: true })
    expect(await page.evaluate(() => window.shared.getVideoTracks().map((track) => track.readyState))).toEqual([
      'ended',
    ])
    expect(await page.evaluate(() => window.shared.getAudioTracks().map((track) => track.readyState))).toEqual(['live'])
    expect(await page.$eval('select[aria-label="Input"]', (s) => (s as HTMLSelectElement).value)).toBe('tab')
    expect(await low(page)).toBeGreaterThan(50)
    expect(await error(page)).toBeNull()
    await page.close()
  })

  it('says so when the share has no audio, and stops', { timeout: 60_000 }, async () => {
    await share(false)
    await page.waitForFunction(() => document.querySelector('.listen .error'), { timeout: 20_000 })
    expect(await error(page)).toBe('No tab audio: pick a tab and tick Share tab audio')
    expect(await page.evaluate(() => window.shared.getTracks().map((track) => track.readyState))).toEqual(['ended'])
    await new Promise((resolve) => setTimeout(resolve, 500))
    expect(await page.evaluate(() => window.sent.length)).toBe(0)
    await page.close()
  })

  it('stops, and says so, when the share ends', { timeout: 60_000 }, async () => {
    await share(true)
    await page.waitForFunction(() => window.sent.some((m) => m.low > 0.5), { timeout: 20_000 })
    // as the browser ends the track when the tab closes or its sharing stops
    await page.evaluate(() => window.shared.getAudioTracks()[0].dispatchEvent(new Event('ended')))
    await page.waitForFunction(() => document.querySelector('.listen .error'), { timeout: 5_000 })
    expect(await error(page)).toBe('The tab stopped sharing its audio')
    expect(await low(page)).toBe(0)
    const sent = await page.evaluate(() => window.sent.length)
    await new Promise((resolve) => setTimeout(resolve, 500))
    expect(await page.evaluate(() => window.sent.length)).toBe(sent)
    await page.close()
  })
})
