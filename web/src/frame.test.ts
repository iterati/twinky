import { describe, expect, it } from 'vitest'
import { WARM_WHITE, decodeFrame } from './frame'

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
})
