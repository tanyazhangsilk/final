import { mount } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ElementPlus from 'element-plus'

import PricingSettings from '../src/views/stations/PricingSettings.vue'

vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    },
  }
})

describe('PricingSettings', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('opens apply dialog and applies selected stations', async () => {
    const wrapper = mount(PricingSettings, { global: { plugins: [ElementPlus] } })
    const vm = wrapper.vm

    vm.openStationDialog(vm.templates[0])
    expect(vm.dialogVisible).toBe(true)

    vm.selectedStations = [{ id: 101, name: '南山区高新园超级超充站', region: '南山区' }]
    vm.submitStationApply()

    const { ElMessage } = await import('element-plus')
    expect(ElMessage.success).toHaveBeenCalled()
    expect(vm.dialogVisible).toBe(false)
  })
})
