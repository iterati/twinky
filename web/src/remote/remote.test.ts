import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import Pin from './Pin'
import { cardControls, knob, ringTurn, stepped, type Feature, type Walk as WalkState } from './remote'
import Walk from './Walk'

function feature(on: number | null, names: string[]): Feature {
  return { name: 'Flicker', switch: on, controls: names.map((name) => ({ name, options: ['a', 'b'], pick: 0 })) }
}

describe('cardControls', () => {
  it('leaves the On switch to the header, keeping each control its visible index', () => {
    const rows = cardControls(feature(0, ['Enabled', 'Start', 'Curved']))
    expect(rows.map(({ control, index }) => [control.name, index])).toEqual([
      ['Start', 1],
      ['Curved', 2],
    ])
  })

  it('shows no rows for a feature switched off', () => {
    expect(cardControls(feature(0, ['Enabled']))).toEqual([])
  })

  it('takes a switch from among the rows', () => {
    // Spiral's Enabled, after Repeats and Mirrored
    const rows = cardControls(feature(2, ['Repeats', 'Mirrored', 'Enabled', 'Twists']))
    expect(rows.map(({ index }) => index)).toEqual([0, 1, 3])
  })

  it('shows every control of a feature with no switch', () => {
    expect(cardControls(feature(null, ['Transition', 'Grain'])).map(({ index }) => index)).toEqual([0, 1])
  })
})

describe('stepped', () => {
  it('wraps round the options both ways', () => {
    expect(stepped(0, -1, 4)).toBe(3)
    expect(stepped(3, 1, 4)).toBe(0)
    expect(stepped(1, 1, 4)).toBe(2)
    expect(stepped(0, 1, 1)).toBe(0)
  })
})

describe('ringTurn', () => {
  const center = { x: 100, y: 100 }

  it('turns the tree back a quarter for a quarter clockwise on the screen', () => {
    // right to bottom, with y down
    expect(ringTurn(0, center, { x: 180, y: 100 }, { x: 100, y: 180 })).toBeCloseTo(-0.25)
    expect(ringTurn(0.5, center, { x: 100, y: 180 }, { x: 180, y: 100 })).toBeCloseTo(0.75)
  })

  it('goes the short way past the seam, and keeps counting round', () => {
    // just above the left to just below it: a sliver anticlockwise, not most of a turn
    const turn = ringTurn(2, center, { x: 20, y: 99 }, { x: 20, y: 101 })
    expect(turn).toBeGreaterThan(2)
    expect(turn).toBeLessThan(2.01)
  })

  it('keeps the knob under the finger', () => {
    for (const start of [0, 0.3, -1.2]) {
      const finger = { x: 30, y: 60 }
      const at = knob(ringTurn(start, center, knob(start, center, 80), finger), center, 80)
      const direction = Math.atan2(finger.y - center.y, finger.x - center.x)
      expect(Math.atan2(at.y - center.y, at.x - center.x)).toBeCloseTo(direction)
    }
  })

  it('puts the knob at the bottom at home', () => {
    const at = knob(0, center, 80)
    expect(at.x).toBeCloseTo(100)
    expect(at.y).toBeCloseTo(180)
  })
})

// a tag of the markup by its aria-label, and the text of the markup, its tags and React's comments gone
const tag = (html: string, label: string) =>
  html.match(new RegExp(`<button[^>]*aria-label="${label}"[^>]*>`))?.[0] ?? ''
const text = (html: string) =>
  html
    .replace(/<[^>]*>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

describe('the Walk card', () => {
  const walk: WalkState = {
    pace: { name: 'Pace', options: ['slow', 'easy', 'brisk', 'fast'], pick: 1 },
    reach: { name: 'Reach', options: ['near', 'far', 'any', 'jump'], pick: 0 },
    stay: false,
    pins: [],
    back: false,
  }
  const card = (state: WalkState, paused: boolean) =>
    renderToStaticMarkup(createElement(Walk, { walk: state, paused, send: () => {} }))

  it('shows Pace and Reach as steppers, Stay and its On switch, and Back and Nudge', () => {
    const html = card(walk, true)
    expect(text(html)).toBe('Walk − Pace: easy + − Reach: near + Stay on this pattern Back Nudge')
    for (const label of ['Pace down', 'Pace up', 'Reach down', 'Reach up']) expect(tag(html, label)).not.toBe('')
    expect(tag(html, 'Walk On')).toContain('aria-checked="false"')
    expect(tag(html, 'Walk Stay')).toContain('aria-checked="false"')
    expect(html).toMatch(/<button disabled="">Back<\/button>/)
  })

  it('says when it walks, stays and has a step to go back', () => {
    const html = card({ ...walk, stay: true, back: true, reach: { ...walk.reach, pick: 3 } }, false)
    expect(tag(html, 'Walk On')).toContain('aria-checked="true"')
    expect(tag(html, 'Walk Stay')).toContain('aria-checked="true"')
    expect(html).toMatch(/<button>Back<\/button>/)
    expect(text(html)).toContain('Reach: jump')
  })
})

describe('the pin', () => {
  it('names its feature and says whether it holds', () => {
    for (const pinned of [true, false]) {
      const html = renderToStaticMarkup(createElement(Pin, { name: 'Pulse', pinned, onClick: () => {} }))
      expect(tag(html, 'Pin Pulse')).toContain(`aria-pressed="${pinned}"`)
      expect(tag(html, 'Pin Pulse')).toContain('class="pin"')
    }
  })
})
