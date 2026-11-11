// What twinky sends at /ws: the layout as JSON on connect, then a binary message a frame

export type Light = {
  x: number
  y: number // its height, 0 to 1
  z: number
  strand: number
  index: number // on its strand
  angle: number // round the trunk, 0 to 1
}

export type Layout = Light[]

// What the W LEDs add, for each 1 of W: a warm white, in linear light as the R, G and B are
export const WARM_WHITE = [1, 0.6, 0.3] as const

export function parseLayout(message: string): Layout {
  return (JSON.parse(message) as { layout: Layout }).layout
}

/** Reads a frame (a 4-byte frame number, little-endian, then W, R, G, B a light) into colors, R, G
 * and B a light from 0 to 1 with W added as warm white, and gives its number. */
export function decodeFrame(data: ArrayBuffer, colors: Float32Array): number {
  const view = new DataView(data)
  const bytes = new Uint8Array(data, 4)
  for (let i = 0; i < colors.length / 3; i++) {
    const w = bytes[i * 4]
    for (let c = 0; c < 3; c++) {
      colors[i * 3 + c] = (bytes[i * 4 + 1 + c] + w * WARM_WHITE[c]) / 255
    }
  }
  return view.getUint32(0, true)
}
