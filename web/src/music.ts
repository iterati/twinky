// Music analysis: blocks of sound in, beats, bands, tone and drive out. Pure, with no page, no Web
// Audio and nothing of twinky in it, so anything that can hand it samples can use it.

export type MusicFeatures = {
  time: number // seconds of sound taken so far: everything below is as of its end
  bpm: number // 0 until a tempo is found
  beat: number // beats counted at time, the fraction its phase: 0 on a beat
  bar: number // whole bars counted at time, 4 beats a bar
  confidence: number // how well the onsets land on the beat, 0 to 1
  low: number // 40-150 Hz, 0 to 1 of its range over the last 10 s
  mid: number // 150 Hz-2 kHz, likewise
  high: number // 2-12 kHz, likewise
  tone: number // the spectral centroid over 4 s, 0 dark to 1 light
  drive: number // kick punch, onset density and beat confidence, 0 groove to 1 drive
  onset: boolean // whether an onset was heard in the samples just taken
}

// The analysis window, in samples, and how many analysis frames a second
const SIZE = 4096
const FRAMES_PER_SECOND = 60
// The tempo's range and the range it prefers, in bpm, and the onset envelope it reads, in seconds
const SLOWEST = 70
const FASTEST = 180
const PREFERRED = [90, 140] as const
const TEMPO_SPAN = 8
// The bands, in Hz
const BANDS = [
  [40, 150],
  [150, 2000],
  [2000, 12000],
] as const
const RANGE_SPAN = 10
const TONE_SPAN = 4
// The centroids, in Hz, that read as 0 and 1
const DARK = 250
const LIGHT = 4000
// Below this a frame is silence, in dB of power against a full-scale sine's 0
const SILENCE = -80
// An onset is placed this many seconds after the middle of the frame its flux peaks in, as measured
// on click tracks: the window's weight is low at its ends, so the flux peaks once a sound is near
// the middle
const ONSET_LAG = 0.0085

/** A 4-term Blackman-Harris window: its low sidelobes keep a bass note out of the mid band. */
function blackmanHarris(size: number): Float64Array {
  const w = new Float64Array(size)
  for (let i = 0; i < size; i++) {
    const x = (2 * Math.PI * i) / (size - 1)
    w[i] = 0.35875 - 0.48829 * Math.cos(x) + 0.14128 * Math.cos(2 * x) - 0.01168 * Math.cos(3 * x)
  }
  return w
}

/** An in-place radix-2 FFT of re and im, their length a power of 2. */
export function fft(re: Float64Array, im: Float64Array) {
  const n = re.length
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1
    for (; j & bit; bit >>= 1) j ^= bit
    j ^= bit
    if (i < j) {
      ;[re[i], re[j]] = [re[j], re[i]]
      ;[im[i], im[j]] = [im[j], im[i]]
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const angle = (-2 * Math.PI) / len
    const wr = Math.cos(angle)
    const wi = Math.sin(angle)
    for (let start = 0; start < n; start += len) {
      let cr = 1
      let ci = 0
      for (let k = 0; k < len / 2; k++) {
        const a = start + k
        const b = a + len / 2
        const tr = re[b] * cr - im[b] * ci
        const ti = re[b] * ci + im[b] * cr
        re[b] = re[a] - tr
        im[b] = im[a] - ti
        re[a] += tr
        im[a] += ti
        const next = cr * wr - ci * wi
        ci = cr * wi + ci * wr
        cr = next
      }
    }
  }
}

/** The last `length` values pushed, oldest first. */
class History {
  readonly values: Float64Array
  private next = 0
  count = 0

  constructor(length: number, fill = 0) {
    this.values = new Float64Array(length).fill(fill)
  }

  push(value: number) {
    this.values[this.next] = value
    this.next = (this.next + 1) % this.values.length
    this.count = Math.min(this.count + 1, this.values.length)
  }

  /** The value `back` pushes ago, 0 the latest. */
  at(back: number): number {
    const n = this.values.length
    return this.values[(this.next - 1 - back + 2 * n) % n]
  }
}

const clamp01 = (x: number) => Math.min(1, Math.max(0, x))

/** How much the tempo search prefers a tempo: fully within 90-140 bpm, a little less an octave out. */
function preference(bpm: number): number {
  const out = bpm < PREFERRED[0] ? Math.log2(PREFERRED[0] / bpm) : Math.log2(Math.max(1, bpm / PREFERRED[1]))
  return Math.exp(-0.5 * out * out)
}

/** Takes sound a block at a time, analyses it about 60 times a second, and gives its features. */
export class MusicAnalyser {
  readonly sampleRate: number
  readonly hop: number // samples between analysis frames
  readonly frameRate: number // analysis frames a second

  private window = blackmanHarris(SIZE)
  private amplitudeScale: number // a bin's magnitude to its sine's amplitude
  private powerScale: number // a band's summed squared magnitudes to its mean-square level
  private bins: [number, number][] // each band's first and last bin
  private fluxBins: [number, number]
  private fluxWeights: Float64Array // each octave alike, so a kick counts as much as a hat
  private samples = new Float32Array(SIZE)
  private written = 0 // samples taken
  private sinceFrame = 0
  private re = new Float64Array(SIZE)
  private im = new Float64Array(SIZE)
  private lastLog = new Float64Array(SIZE / 2)

  // onsets: the flux a frame over the tempo span, and the peak picking's last frames
  private flux: History
  private fluxTimes = new History(3)
  private thresholds = new History(3)
  private lastOnset = -Infinity
  private onsets: number[] = [] // the last 4 s's onset times
  private heard = false

  // the beat: a beat's number and time, and the period, 0 until a tempo is found
  private period = 0
  private beatCount = 0
  private beatTime = 0
  private confidence = 0
  private framesToTempo = 0
  private tapped = { bpm: 0, until: -Infinity }
  private taps: number[] = []

  // the bands' levels in dB, after their attack and release, and their 10 s history
  private levels = BANDS.map(() => SILENCE * 1.5)
  private levelHistory: History[]
  private bandValues = BANDS.map(() => 0)
  private tones: History
  private punch = 0
  private drive = 0

  constructor(sampleRate: number) {
    this.sampleRate = sampleRate
    this.hop = Math.round(sampleRate / FRAMES_PER_SECOND)
    this.frameRate = sampleRate / this.hop
    const sum = this.window.reduce((a, b) => a + b, 0)
    const squares = this.window.reduce((a, b) => a + b * b, 0)
    this.amplitudeScale = 2 / sum
    this.powerScale = 2 / (SIZE * squares)
    const bin = (hz: number) => Math.min(SIZE / 2 - 1, Math.round((hz * SIZE) / sampleRate))
    this.bins = BANDS.map(([lo, hi]) => [bin(lo), bin(hi) - 1])
    this.fluxBins = [bin(30), bin(12000)]
    this.fluxWeights = new Float64Array(SIZE / 2)
    let weights = 0
    for (let k = this.fluxBins[0]; k <= this.fluxBins[1]; k++) weights += this.fluxWeights[k] = 1 / k
    this.fluxWeights.forEach((w, k) => (this.fluxWeights[k] = w / weights))
    this.flux = new History(Math.round(TEMPO_SPAN * this.frameRate))
    this.levelHistory = BANDS.map(() => new History(Math.round(RANGE_SPAN * this.frameRate), SILENCE * 1.5))
    this.tones = new History(Math.round(TONE_SPAN * this.frameRate))
  }

  /** Takes the next samples, of any length, and gives the features as of their end. */
  analyse(block: Float32Array): MusicFeatures {
    this.heard = false
    for (const sample of block) {
      this.samples[this.written % SIZE] = sample
      this.written++
      if (++this.sinceFrame === this.hop) {
        this.sinceFrame = 0
        if (this.written >= SIZE) this.frame()
      }
    }
    const time = this.written / this.sampleRate
    const beat = this.period ? this.beatAt(time) : 0
    return {
      time,
      bpm: this.period ? 60 / this.period : 0,
      beat,
      bar: Math.floor(beat / 4),
      confidence: this.confidence,
      low: this.bandValues[0],
      mid: this.bandValues[1],
      high: this.bandValues[2],
      tone: this.tones.count
        ? this.tones.values.slice(0, this.tones.count).reduce((a, b) => a + b, 0) / this.tones.count
        : 0.5,
      drive: this.drive,
      onset: this.heard,
    }
  }

  /** A tap of the tempo, at a time on the analyser's clock (MusicFeatures.time): from the second tap
   * on, the beat lands on the taps, and the tempo search keeps near their tempo for 30 s. */
  tap(time: number) {
    this.taps = this.taps.filter((t) => time - t < 2.5)
    this.taps.push(time)
    if (this.taps.length < 2) return
    const period = (this.taps[this.taps.length - 1] - this.taps[0]) / (this.taps.length - 1)
    this.tapped = { bpm: 60 / period, until: time + 30 }
    this.beatCount = this.period ? Math.round(this.beatAt(time)) : 0
    this.beatTime = time
    this.period = period
    this.confidence = Math.max(this.confidence, 0.5)
  }

  private beatAt(time: number): number {
    return this.beatCount + (time - this.beatTime) / this.period
  }

  private frame() {
    const { re, im } = this
    for (let i = 0; i < SIZE; i++) {
      re[i] = this.samples[(this.written + i) % SIZE] * this.window[i]
      im[i] = 0
    }
    fft(re, im)

    // the flux on log magnitudes, the bands' power, and the centroid
    let flux = 0
    let total = 0
    let weighted = 0
    const power = BANDS.map(() => 0)
    for (let k = 1; k < SIZE / 2; k++) {
      const squared = re[k] * re[k] + im[k] * im[k]
      const magnitude = Math.sqrt(squared) * this.amplitudeScale
      const log = Math.log1p(1000 * magnitude)
      if (k >= this.fluxBins[0] && k <= this.fluxBins[1]) {
        flux += this.fluxWeights[k] * Math.max(0, log - this.lastLog[k])
        total += magnitude
        weighted += magnitude * Math.log2((k * this.sampleRate) / SIZE)
      }
      this.lastLog[k] = log
      this.bins.forEach(([lo, hi], b) => {
        if (k >= lo && k <= hi) power[b] += squared
      })
    }
    const time = (this.written - SIZE / 2) / this.sampleRate // the window's middle

    this.onsetFrame(flux, time)
    if (--this.framesToTempo <= 0) {
      this.framesToTempo = 6
      this.findTempo(time)
    }
    if (time - this.lastOnset > 2) this.confidence *= 0.99
    this.bandFrame(power.map((p) => 10 * Math.log10(p * this.powerScale + 1e-12)))
    if (total > 0) {
      const level = 20 * Math.log10(total / (this.fluxBins[1] - this.fluxBins[0] + 1) + 1e-12)
      if (level > SILENCE - 30) {
        this.tones.push(clamp01((weighted / total - Math.log2(DARK)) / Math.log2(LIGHT / DARK)))
      }
    }
    const rate = this.onsets.length / TONE_SPAN
    const target = 0.4 * this.punch + 0.3 * clamp01(rate / 4) + 0.3 * this.confidence
    this.drive += (target - this.drive) * (1 - Math.exp(-1 / (2 * this.frameRate)))
    this.punch *= Math.exp(-1 / (4 * this.frameRate))
  }

  /** Picks the flux's peaks over its adaptive threshold, a frame late, and nudges the beat to each. */
  private onsetFrame(flux: number, time: number) {
    this.flux.push(flux)
    this.fluxTimes.push(time)
    let recent = 0
    const span = Math.min(this.flux.count, Math.round(0.5 * this.frameRate))
    for (let i = 0; i < span; i++) recent += this.flux.at(i)
    this.thresholds.push(0.01 + (1.5 * recent) / span)
    if (this.flux.count < 3) return

    const [after, peak, before] = [this.flux.at(0), this.flux.at(1), this.flux.at(2)]
    if (!(peak > this.thresholds.at(1) && peak >= before && peak > after)) return
    const curve = before - 2 * peak + after
    const offset = curve < 0 ? (0.5 * (before - after)) / curve : 0
    const onset = this.fluxTimes.at(1) + offset / this.frameRate + ONSET_LAG
    if (onset - this.lastOnset < 0.1) return
    this.lastOnset = onset
    this.heard = true
    this.onsets = this.onsets.filter((t) => onset - t < TONE_SPAN)
    this.onsets.push(onset)
    const jump = this.levels[0] - this.levelHistory[0].at(Math.min(3, this.levelHistory[0].count - 1))
    this.punch += (clamp01(jump / 12) - this.punch) * 0.25

    if (!this.period) return
    const position = this.beatAt(onset)
    const nearest = Math.round(position)
    const off = position - nearest
    if (Math.abs(off) < 0.2) {
      const error = off * this.period
      this.beatTime = onset - error * 0.75
      this.beatCount = nearest
      this.period += error * 0.05
      this.confidence += (1 - 5 * Math.abs(off) - this.confidence) * 0.15
    } else {
      this.confidence *= 0.97
    }
  }

  /** How well a beat every `period` seconds through `beat` lines up with the onset envelope's last
   * 8 s, to `time`, its latest frame. */
  private gridScore(beat: number, period: number, time: number): number {
    const fr = this.frameRate
    let score = 0
    const latest = beat + Math.floor((time - ONSET_LAG - beat) / period) * period
    for (let t = latest; ; t -= period) {
      const back = (time - ONSET_LAG - t) * fr
      if (back >= this.flux.count - 1) return score
      const i = Math.floor(back)
      score += this.flux.at(i) + (this.flux.at(i + 1) - this.flux.at(i)) * (back - i)
    }
  }

  /** The beat, a beat every `period` seconds, that lines up best with the onset envelope, and how well. */
  private bestGrid(period: number, time: number): { beat: number; score: number } {
    let best = { beat: time, score: -Infinity }
    for (let back = 0; back < period * this.frameRate; back += 0.5) {
      const beat = time - back / this.frameRate
      const score = this.gridScore(beat, period, time)
      if (score > best.score) best = { beat, score }
    }
    return best
  }

  /** Autocorrelates the onset envelope over the last 8 s, scoring each tempo by its first 4 periods.
   * When the tempo it finds is more than 4% from the beat's, the beat starts over on it, on the grid
   * that best fits the onsets; and the beat moves to a better grid when one fits clearly better. */
  private findTempo(time: number) {
    const fr = this.frameRate
    const n = this.flux.count
    if (n < 3 * fr) return
    const maxLag = Math.ceil((4 * 60 * fr) / SLOWEST) + 1
    const envelope = new Float64Array(n)
    let mean = 0
    for (let i = 0; i < n; i++) mean += envelope[i] = this.flux.at(n - 1 - i)
    mean /= n
    for (let i = 0; i < n; i++) envelope[i] -= mean
    const ac = new Float64Array(maxLag + 2)
    for (let lag = 0; lag < Math.min(maxLag + 2, n); lag++) {
      let sum = 0
      for (let i = lag; i < n; i++) sum += envelope[i] * envelope[i - lag]
      ac[lag] = sum
    }
    const at = (lag: number) => {
      const i = Math.floor(lag)
      return ac[i] + (ac[i + 1] - ac[i]) * (lag - i)
    }

    const near = time < this.tapped.until
    const lo = near ? Math.max(SLOWEST, this.tapped.bpm * 0.85) : SLOWEST
    const hi = near ? Math.min(FASTEST, this.tapped.bpm / 0.85) : FASTEST
    const step = 0.25
    const scores: number[] = []
    for (let bpm = lo; bpm <= hi; bpm += step) {
      const period = (60 * fr) / bpm
      let score = 0
      for (let m = 1; m <= 4; m++) score += at(m * period)
      scores.push(score * preference(bpm))
    }
    let best = 0
    scores.forEach((s, i) => {
      if (s > scores[best]) best = i
    })
    if (scores[best] <= 0) return
    let shift = 0
    if (best > 0 && best < scores.length - 1) {
      const curve = scores[best - 1] - 2 * scores[best] + scores[best + 1]
      if (curve < 0) shift = (0.5 * (scores[best - 1] - scores[best + 1])) / curve
    }
    const period = 60 / (lo + (best + shift) * step)

    const fresh = !this.period || Math.abs(period / this.period - 1) > 0.04
    const grid = this.bestGrid(fresh ? period : this.period, time)
    const off = this.period ? this.beatAt(grid.beat) - Math.round(this.beatAt(grid.beat)) : 0
    if (fresh || (Math.abs(off) > 0.15 && grid.score > 1.3 * this.gridScore(this.beatTime, this.period, time))) {
      this.beatCount = this.period ? Math.round(this.beatAt(grid.beat)) : 0
      this.beatTime = grid.beat
      if (fresh) this.period = period
    }
  }

  /** Each band's level with a fast attack and a slow release, auto-gained by its own 10 s range:
   * its ceiling no more than 20 dB under the loudest band's, and its floor 24 to 48 dB below that. */
  private bandFrame(decibels: number[]) {
    const release = 1 - Math.exp(-1 / (0.25 * this.frameRate))
    const ranges = decibels.map((db, b) => {
      const level = this.levels[b]
      this.levels[b] = level + (db - level) * (db > level ? 0.6 : release)
      const history = this.levelHistory[b]
      history.push(this.levels[b])
      let min = Infinity
      let max = -Infinity
      for (const v of history.values) {
        min = Math.min(min, v)
        max = Math.max(max, v)
      }
      return [min, max]
    })
    const loudest = Math.max(...ranges.map(([, max]) => max))
    ranges.forEach(([min, max], b) => {
      const ceiling = Math.max(max, loudest - 20, SILENCE)
      const floor = Math.min(Math.max(min, ceiling - 48), ceiling - 24)
      this.bandValues[b] = clamp01((this.levels[b] - floor) / (ceiling - floor))
    })
  }
}
