import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FormatDriveModal from '@/components/FormatDriveModal.vue'

const mockApi = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('@/services/api', () => ({ default: mockApi }))
beforeEach(() => {
  mockApi.post.mockReset()
  mockApi.post.mockResolvedValue({ data: {
    dry_run: true, drive: { device_id: 'synthetic-device', name: 'BIRDSTORE', path: '/dev/sda', size_bytes: 500000000000 },
    filesystem: 'ext4', erases_all_data: true, formatting_enabled: false
  } })
})

enableAutoUnmount(afterEach)
const mountDialog = () => mount(FormatDriveModal, {
  attachTo: document.body,
  props: { drive: { name: 'BIRDSTORE', path: '/dev/sda', device_id: 'synthetic-device' }, sizeLabel: '500 GB' }
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
    const check = wrapper.findAll('button').find(button => button.text() === 'Check plan')
    expect(check.element.disabled).toBe(true)
    await input.setValue('wrong drive')
    expect(input.attributes('aria-invalid')).toBe('true')
    await input.setValue('BIRDSTORE')
    expect(wrapper.text()).toContain('Drive name matches.')
    expect(input.attributes('aria-invalid')).toBe('false')
    expect(check.element.disabled).toBe(false)
    await check.trigger('click')
    await flushPromises()
    expect(mockApi.post).toHaveBeenCalledWith('/system/storage/format-dry-run', {
      path: '/dev/sda', device_id: 'synthetic-device', confirmation: 'BIRDSTORE'
    })
    expect(wrapper.text()).toContain('Would erase all data on /dev/sda and format it as ext4. No changes made.')
    const format = wrapper.findAll('button').find(button => button.text() === 'Format drive')
    expect(format.element.disabled).toBe(true)
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })

  it('shows a rejected plan without enabling formatting', async () => {
    mockApi.post.mockRejectedValue({ response: { data: { error: 'Drive information changed.' } } })
    const wrapper = mountDialog()
    await wrapper.get('input').setValue('BIRDSTORE')
    await wrapper.findAll('button').find(button => button.text() === 'Check plan').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toBe('Drive information changed.')
    expect(wrapper.text()).toContain('Formatting is disabled.')
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })

  it('allows Escape to dismiss the preview', async () => {
    const wrapper = mountDialog()
    await wrapper.get('dialog').trigger('cancel')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
