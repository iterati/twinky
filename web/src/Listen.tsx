import { useEffect, useRef, useState } from 'react'
import captureUrl from './capture.worklet.ts?worker&url'
import { MusicAnalyser, type MusicFeatures } from './music'

// About 30 music messages a second to twinky
const SEND_EVERY = 1 / 30

/** The Mac's ears: a mic or line-in, analysed here and sent to twinky, whose Music feature links it to
 * the tree. Its meters show what twinky is told. */
export default function Listen({ send }: { send: (message: string) => void }) {
  // the input listened to, '' the default one, null not listening
  const [input, setInput] = useState<string | null>(null)
  const [inputs, setInputs] = useState<MediaDeviceInfo[]>([])
  const [features, setFeatures] = useState<MusicFeatures | null>(null)
  const [error, setError] = useState<string | null>(null)
  // the analyser, and the latest features with when, on the Mac's clock, they came
  const listening = useRef<{ analyser: MusicAnalyser; features: MusicFeatures; at: number } | null>(null)

  useEffect(() => {
    if (input === null) return
    const context = new AudioContext()
    let stream: MediaStream | null = null
    let stopped = false
    const start = async () => {
      // the browser's voice processing wrecks music, so all of it is off
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: input ? { exact: input } : undefined,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      })
      if (stopped) return stream.getTracks().forEach((track) => track.stop())
      // the inputs' names only come once the browser may listen
      setInputs((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'audioinput'))
      await context.audioWorklet.addModule(captureUrl)
      if (stopped) return
      const node = new AudioWorkletNode(context, 'capture')
      const analyser = new MusicAnalyser(context.sampleRate)
      let sent = 0
      node.port.onmessage = (event: MessageEvent<Float32Array>) => {
        const f = analyser.analyse(event.data)
        const at = Date.now() / 1000
        listening.current = { analyser, features: f, at }
        if (at - sent < SEND_EVERY) return
        sent = at
        const { bpm, beat, bar, confidence, low, mid, high, tone, drive } = f
        send(JSON.stringify({ music: { time: at, bpm, beat, bar, confidence, low, mid, high, tone, drive } }))
        setFeatures(f)
      }
      context.createMediaStreamSource(stream).connect(node)
      // the node writes silence, but only a node the speakers pull from runs
      node.connect(context.destination)
      await context.resume()
    }
    start().catch((e: Error) => setError(e.message))
    return () => {
      stopped = true
      stream?.getTracks().forEach((track) => track.stop())
      void context.close()
      listening.current = null
      setFeatures(null)
    }
  }, [input, send])

  const tap = () => {
    const l = listening.current
    if (l) l.analyser.tap(l.features.time + (Date.now() / 1000 - l.at))
  }

  if (input === null) {
    return (
      <section className="listen">
        <button
          onClick={() => {
            setError(null)
            setInput('')
          }}
        >
          Listen
        </button>
      </section>
    )
  }

  const phase = features && features.bpm ? features.beat % 1 : 1
  return (
    <section className="listen" aria-label="Listen">
      <div className="row">
        <select value={input} onChange={(e) => setInput(e.target.value)} aria-label="Input">
          <option value="">Default input</option>
          {inputs.map((d) => (
            <option key={d.deviceId} value={d.deviceId}>
              {d.label || 'Input'}
            </option>
          ))}
        </select>
        <button onClick={() => setInput(null)}>Stop</button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="row">
        <span
          className="beat"
          style={{ opacity: 0.15 + 0.85 * (features?.confidence ?? 0) * (1 - phase) ** 3 }}
          aria-label="Beat"
        />
        <span className="bpm">
          {features?.bpm ? features.bpm.toFixed(1) : '--'}
          <small> bpm</small>
        </span>
        <button onClick={tap}>Tap</button>
      </div>
      {(['low', 'mid', 'high'] as const).map((band) => (
        <div className="meter" key={band}>
          <span>{band}</span>
          <div>
            <div style={{ width: `${100 * (features?.[band] ?? 0)}%` }} />
          </div>
        </div>
      ))}
    </section>
  )
}
