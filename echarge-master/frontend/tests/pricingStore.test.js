import { describe, expect, it } from 'vitest'

import { saveTemplateToList } from '../src/utils/pricingStore'

describe('pricing store', () => {
  it('updates template name and periods on save', () => {
    const templates = [
      { id: 'tpl-1', name: 'old', isDefault: false, stationIds: [], periods: [] },
      { id: 'tpl-2', name: 'keep', isDefault: false, stationIds: [], periods: [] },
    ]

    const next = saveTemplateToList(
      templates,
      'tpl-1',
      { name: ' new-name ', isDefault: true, stationIds: ['st-1'] },
      [{ id: 'p1', timeRange: ['00:00', '24:00'] }]
    )

    expect(next[0].name).toBe('new-name')
    expect(next[0].isDefault).toBe(true)
    expect(next[0].stationIds).toEqual(['st-1'])
    expect(next[0].periods).toHaveLength(1)
    expect(next[1].name).toBe('keep')
  })
})

