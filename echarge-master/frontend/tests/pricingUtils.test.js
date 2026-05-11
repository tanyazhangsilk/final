import { describe, expect, it } from 'vitest'

import { hasOverlap } from '../src/utils/pricing'

describe('pricing utils', () => {
  it('detects overlapping periods', () => {
    const periods = [
      { timeRange: ['08:00', '10:00'] },
      { timeRange: ['09:30', '12:00'] },
    ]
    expect(hasOverlap(periods)).toBe(true)
  })

  it('does not flag non-overlapping periods', () => {
    const periods = [
      { timeRange: ['08:00', '10:00'] },
      { timeRange: ['10:00', '12:00'] },
    ]
    expect(hasOverlap(periods)).toBe(false)
  })
})

