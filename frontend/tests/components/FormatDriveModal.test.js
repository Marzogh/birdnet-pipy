import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import FormatDriveModal from '@/components/FormatDriveModal.vue'

enableAutoUnmount(afterEach)
const mountDialog = () => mount(FormatDriveModal, {
  attachTo: document.body,
  props: { drive: { name: 'BIRDSTORE', path: '/dev/sda' }, sizeLabel: '500 GB' }
})

describe('Format drive confirmation preview', () => {
  it('identifies the drive, checks the typed name and keeps formatting disabled', async () => {
    const wrapper = mountDialog()
    expect(wrapper.get('dialog').attributes('open')).toBeDefined()
    expect(wrapper.text()).toContain('BIRDSTORE · 500 GB')
    expect(wrapper.text()).toContain('/dev/sda')
    expect(wrapper.text()).toContain('Formatting will erase all data on this drive.')
    expect(wrapper.text()).toContain('ext4')
    const input = wrapper.get('input')
    const format = wrapper.findAll('button').find(button => button.text() === 'Format drive')
    expect(format.element.disabled).toBe(true)
    await input.setValue('wrong drive')
    expect(input.attributes('aria-invalid')).toBe('true')
    await input.setValue('BIRDSTORE')
    expect(wrapper.text()).toContain('Drive name matches.')
    expect(input.attributes('aria-invalid')).toBe('false')
    expect(format.element.disabled).toBe(true)
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })

  it('allows Escape to dismiss the preview', async () => {
    const wrapper = mountDialog()
    await wrapper.get('dialog').trigger('cancel')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
