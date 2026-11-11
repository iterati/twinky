import { describe, expect, it } from 'vitest'
import { WARM_WHITE, decodeFrame, parseLayout } from './frame'

function frame(number: number, lights: number[][]): ArrayBuffer {
  const data = new ArrayBuffer(4 + lights.length * 4)
  new DataView(data).setUint32(0, number, true)
  new Uint8Array(data, 4).set(lights.flat())
  return data
}

describe('decodeFrame', () => {
  it('reads the frame number, little-endian', () => {
    expect(decodeFrame(frame(0x01020304, [[0, 0, 0, 0]]), new Float32Array(3))).toBe(0x01020304)
    expect(decodeFrame(frame(4_000_000_000, [[0, 0, 0, 0]]), new Float32Array(3))).toBe(4_000_000_000)
  })

  it('gives each light its R, G and B with W added as warm white', () => {
    const colors = new Float32Array(9)
    decodeFrame(
      frame(7, [
        [0, 255, 0, 0],
        [255, 0, 0, 0],
        [51, 0, 102, 204],
      ]),
      colors,
    )
    const expected = [
      [1, 0, 0],
      [...WARM_WHITE],
      [0.2 * WARM_WHITE[0], 0.4 + 0.2 * WARM_WHITE[1], 0.8 + 0.2 * WARM_WHITE[2]],
    ].flat()
    expected.forEach((value, i) => expect(colors[i]).toBeCloseTo(value, 6))
  })

  it('reads W as warmer than R, G and B at full', () => {
    expect(WARM_WHITE[0]).toBeGreaterThan(WARM_WHITE[1])
    expect(WARM_WHITE[1]).toBeGreaterThan(WARM_WHITE[2])
  })
})

describe('parseLayout', () => {
  it('gives the lights of the layout message', () => {
    const light = { x: 0.1, y: 0.5, z: -0.2, strand: 1, index: 3, angle: 0.8 }
    expect(parseLayout(JSON.stringify({ layout: [light] }))).toEqual([light])
  })
})
