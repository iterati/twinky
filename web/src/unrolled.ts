import type { Layout } from './frame'

// How far round the trunk is repeated past each edge, so a pattern's wrap shows
export const OVERLAP = 0.25

/** The Unrolled view: each light at its angle across and its height up, and again past the far edge
 * when it's within OVERLAP of the seam. sources gives each point's light. */
export function unroll(layout: Layout): { positions: Float32Array; sources: Uint32Array } {
  const points: [number, number, number][] = []
  layout.forEach((light, i) => {
    points.push([light.angle, light.y, i])
    if (light.angle < OVERLAP) points.push([light.angle + 1, light.y, i])
    if (light.angle > 1 - OVERLAP) points.push([light.angle - 1, light.y, i])
  })
  return {
    positions: new Float32Array(points.flatMap(([x, y]) => [x, y, 0])),
    sources: new Uint32Array(points.map(([, , i]) => i)),
  }
}
