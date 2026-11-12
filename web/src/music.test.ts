import { describe, expect, it } from 'vitest'
import { MusicAnalyser, type MusicFeatures } from './music'

const RATE = 48000
// what the page's worklet hands over at a time
const BLOCK = 512

/** A repeatable white noise, from -1 to 1. */
function noise(seed: number): () => number {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0
    return s / 2 ** 31 - 1
  }
}

/** A click every beat from `first` seconds on: a 2 kHz blip and a noise burst, decaying in 15 ms,
 * over a quiet hiss. */
function clicks(bpm: number, seconds: number, first: number): Float32Array {
  const out = new Float32Array(seconds * RATE)
  const random = noise(bpm)
  const period = 60 / bpm
  for (let i = 0; i < out.length; i++) {
    const t = i / RATE
    const since = (t - first) % period
    const envelope = t >= first ? Math.exp(-since / 0.015) : 0
    out[i] = 0.002 * random() + envelope * (0.5 * Math.sin(2 * Math.PI * 2000 * since) + 0.3 * random())
  }
  return out
}

/** A kick on each beat and a hat on each off-beat, louder than the one on the beat. */
function kicksAndHats(bpm: number, seconds: number): Float32Array {
  const out = new Float32Array(seconds * RATE)
  const random = noise(3)
  const period = 60 / bpm
  for (let i = 0; i < out.length; i++) {
    const beat = i / RATE / period
    const since = (beat % 1) * period
    const sinceEighth = ((beat * 2) % 1) * (period / 2)
    const kick = Math.exp(-since / 0.12) * Math.sin(2 * Math.PI * (50 + 80 * Math.exp(-since / 0.03)) * since)
    const hat = Math.exp(-sinceEighth / 0.02) * random() * (Math.floor(beat * 2) % 2 ? 0.2 : 0.1)
    out[i] = 0.7 * kick + hat
  }
  return out
}

function sine(hz: number, seconds: number): Float32Array {
  const out = new Float32Array(seconds * RATE)
  const random = noise(hz)
  for (let i = 0; i < out.length; i++) out[i] = 0.3 * Math.sin((2 * Math.PI * hz * i) / RATE) + 0.0005 * random()
  return out
}

/** White noise, or noise through a one-pole low-pass at `cutoff` Hz. */
function hiss(seconds: number, cutoff?: number): Float32Array {
  const out = new Float32Array(seconds * RATE)
  const random = noise(7)
  const k = cutoff ? 1 - Math.exp((-2 * Math.PI * cutoff) / RATE) : 1
  let y = 0
  for (let i = 0; i < out.length; i++) {
    y += (random() - y) * k
    out[i] = 0.3 * y
  }
  return out
}

/** Feeds the sound in blocks and gives the features after each. */
function analyse(sound: Float32Array): MusicFeatures[] {
  const analyser = new MusicAnalyser(RATE)
  const out: MusicFeatures[] = []
  for (let i = 0; i < sound.length; i += BLOCK) out.push(analyser.analyse(sound.subarray(i, i + BLOCK)))
  return out
}

describe('the beat', () => {
  it.each([100, 128, 174])('finds a %d bpm click track and its phase within 8 s', (bpm) => {
    const first = 0.137
    const period = 60 / bpm
    const after = analyse(clicks(bpm, 14, first)).filter((f) => f.time >= 8)
    for (const f of after) {
      expect(Math.abs(f.bpm - bpm)).toBeLessThan(1)
      // the beat's phase against the clicks', in seconds, the short way round
      const off = ((((f.beat - (f.time - first) / period) % 1) + 1.5) % 1) - 0.5
      expect(Math.abs(off * period)).toBeLessThan(0.03)
      expect(f.bar).toBe(Math.floor(f.beat / 4))
    }
    expect(after.at(-1)!.confidence).toBeGreaterThan(0.7)
  })

  it('puts the beat on the kicks, not on louder off-beat hats', () => {
    const period = 60 / 128
    for (const f of analyse(kicksAndHats(128, 12)).filter((f) => f.time >= 8)) {
      expect(Math.abs(f.bpm - 128)).toBeLessThan(1)
      const off = ((((f.beat - f.time / period) % 1) + 1.5) % 1) - 0.5
      expect(Math.abs(off * period)).toBeLessThan(0.03)
    }
  })
})

describe('the bands', () => {
  it.each([
    [80, 'low'],
    [600, 'mid'],
    [6000, 'high'],
  ] as const)('puts a %d Hz sine in the %s band', (hz, band) => {
    const f = analyse(sine(hz, 3)).at(-1)!
    for (const other of ['low', 'mid', 'high'] as const) {
      if (other === band) expect(f[other]).toBeGreaterThan(0.8)
      else expect(f[other]).toBeLessThan(0.3)
    }
  })
})

describe('the tone', () => {
  it('reads bright noise lighter than muffled noise', () => {
    const bright = analyse(hiss(5)).at(-1)!.tone
    const muffled = analyse(hiss(5, 400)).at(-1)!.tone
    expect(bright).toBeGreaterThan(muffled + 0.2)
    expect(bright).toBeLessThanOrEqual(1)
    expect(muffled).toBeGreaterThanOrEqual(0)
  })
})
