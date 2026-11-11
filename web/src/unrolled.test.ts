import { describe, expect, it } from 'vitest'
import type { Light } from './frame'
import { unroll } from './unrolled'

function light(angle: number, y: number): Light {
  return { x: 0, y, z: 0, strand: 0, index: 0, angle }
}

function points(angle: number, y: number): number[][] {
  const { positions, sources } = unroll([light(angle, y)])
  expect([...sources]).toEqual(new Array(positions.length / 3).fill(0))
  return Array.from({ length: sources.length }, (_, i) => [...positions.slice(i * 3, i * 3 + 3)])
}

describe('unroll', () => {
  it('draws a light near the seam at both edges', () => {
    expect(points(0.05, 0.3)).toEqual(
      [
        [0.05, 0.3, 0],
        [1.05, 0.3, 0],
      ].map((p) => p.map(Math.fround)),
    )
    expect(points(0.9, 0.7)).toEqual(
      [
        [0.9, 0.7, 0],
        [0.9 - 1, 0.7, 0],
      ].map((p) => p.map(Math.fround)),
    )
  })

  it('draws a light half a turn from the seam once', () => {
    expect(points(0.5, 0.4)).toEqual([[0.5, 0.4, 0]].map((p) => p.map(Math.fround)))
  })

  it('keeps each point to its light', () => {
    const { sources } = unroll([light(0.5, 0), light(0.1, 0), light(0.6, 0)])
    expect([...sources]).toEqual([0, 1, 1, 2])
  })
})
