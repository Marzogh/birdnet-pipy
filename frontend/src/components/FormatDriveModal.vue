<template>
  <dialog
    ref="dialog"
    aria-labelledby="format-drive-title"
    aria-describedby="format-drive-warning format-drive-disabled"
    class="m-auto w-full max-w-sm rounded-xl p-0 shadow-xl backdrop:bg-black/50"
    @cancel.prevent="$emit('close')"
  >
    <div class="relative bg-white p-6">
      <button
        type="button"
        aria-label="Close"
        class="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        @click="$emit('close')"
      >
        <CloseIcon class="h-5 w-5" />
      </button>
      <h2
        id="format-drive-title"
        class="text-lg font-semibold text-gray-900 pr-8 mb-3"
      >
        Format drive
      </h2>
      <p class="text-sm font-medium text-gray-800">
        {{ drive.name }} · {{ sizeLabel }}
      </p>
      <p class="text-xs text-gray-600 mb-4">
        {{ drive.path }}
      </p>
      <p
        id="format-drive-warning"
        class="text-sm font-medium text-red-700 mb-3"
      >
        Formatting will erase all data on this drive.
      </p>
      <p class="text-sm text-gray-700 mb-4">
        New format: <strong>ext4</strong>
      </p>
      <label
        for="format-drive-name"
        class="block text-sm text-gray-700 mb-1"
      >Type “{{ drive.name }}” to confirm</label>
      <input
        id="format-drive-name"
        v-model="confirmation"
        autofocus
        autocomplete="off"
        :spellcheck="false"
        required
        :disabled="checking"
        :aria-invalid="confirmation.length > 0 && !nameMatches"
        aria-describedby="format-drive-match"
        class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-green-600 focus:outline-none focus:ring-1 focus:ring-green-600"
      >
      <p
        id="format-drive-match"
        class="mt-1 text-xs text-gray-600 min-h-4"
        role="status"
      >
        {{ confirmation ? nameMatches ? 'Drive name matches.' : 'Drive name does not match.' : '' }}
      </p>
      <p
        v-if="error"
        class="mt-3 text-sm text-red-700"
        role="alert"
      >
        {{ error }}
      </p>
      <p
        v-if="plan"
        class="mt-3 text-sm text-gray-700"
        role="status"
      >
        Would erase all data on {{ plan.drive.path }} and format it as {{ plan.filesystem }}. No changes made.
      </p>
      <p
        id="format-drive-disabled"
        class="mt-3 text-xs text-gray-600"
      >
        Formatting is disabled.
      </p>
      <div class="flex gap-3 mt-4">
        <button
          type="button"
          class="flex-1 rounded-lg border border-gray-200 py-2 text-sm text-gray-600 hover:bg-gray-100"
          @click="$emit('close')"
        >
          Cancel
        </button>
        <button
          v-if="!plan"
          type="button"
          :disabled="!nameMatches || !drive.device_id || checking"
          :aria-busy="checking"
          class="flex-1 rounded-lg bg-blue-600 py-2 text-sm text-white hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-600 disabled:cursor-not-allowed"
          @click="checkPlan"
        >
          {{ checking ? 'Checking…' : 'Check plan' }}
        </button>
        <button
          v-else
          type="button"
          disabled
          aria-describedby="format-drive-disabled"
          class="flex-1 rounded-lg bg-gray-200 py-2 text-sm text-gray-600 cursor-not-allowed"
        >
          Format drive
        </button>
      </div>
    </div>
  </dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '@/services/api'
import CloseIcon from '@/components/icons/CloseIcon.vue'

const props = defineProps({
  drive: { type: Object, required: true },
  sizeLabel: { type: String, required: true }
})
defineEmits(['close'])

const dialog = ref(null)
const confirmation = ref('')
const checking = ref(false)
const plan = ref(null)
const error = ref('')
watch(confirmation, () => { plan.value = null; error.value = '' })
const checkPlan = async () => {
  if (!nameMatches.value || !props.drive.device_id || checking.value) return
  checking.value = true
  error.value = ''
  try {
    const { data } = await api.post('/system/storage/format-dry-run', {
      path: props.drive.path,
      device_id: props.drive.device_id,
      confirmation: confirmation.value
    })
    plan.value = data
  } catch (failure) {
    error.value = failure.response?.data?.error || 'Could not check the format plan. Try again.'
  } finally {
    checking.value = false
  }
}

const nameMatches = computed(() => confirmation.value === props.drive.name)
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => dialog.value.close())
</script>
