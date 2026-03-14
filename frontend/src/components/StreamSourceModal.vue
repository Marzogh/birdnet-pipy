<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <!-- Backdrop -->
    <div
      class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
      @click="handleBackdropClick"
    />

    <!-- Modal -->
    <div class="flex min-h-full items-center justify-center p-4">
      <div class="relative bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
        <!-- Close button -->
        <button
          v-if="!testing"
          class="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          @click="$emit('close')"
        >
          <svg
            class="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          {{ isEditing ? 'Edit Stream' : 'Add Stream' }}
        </h3>

        <form
          class="space-y-3"
          @submit.prevent="handleSubmit"
        >
          <!-- URL field -->
          <div>
            <label
              for="stream-url"
              class="block text-sm text-gray-600 mb-1"
            >Stream URL</label>
            <input
              id="stream-url"
              ref="urlInput"
              v-model="url"
              type="text"
              class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              placeholder="rtsp://192.168.1.100/stream"
              @input="clearErrors"
            >
          </div>

          <!-- Label field -->
          <div>
            <label
              for="stream-label"
              class="block text-sm text-gray-600 mb-1"
            >Label <span class="text-gray-400 font-normal">(optional)</span></label>
            <input
              id="stream-label"
              v-model="label"
              type="text"
              class="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              placeholder="e.g. Backyard mic"
            >
          </div>

          <!-- Error display -->
          <div
            v-if="error"
            class="text-xs text-red-600 bg-red-50 p-2 rounded-lg"
          >
            <span>{{ error }}</span>
            <button
              v-if="canForceSubmit"
              type="button"
              class="block text-gray-500 hover:text-gray-700 underline mt-1"
              @click="handleForceSubmit"
            >
              {{ isEditing ? 'Save anyway' : 'Add anyway' }}
            </button>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between pt-2">
            <button
              v-if="isEditing"
              type="button"
              class="text-xs text-red-500 hover:text-red-700 transition-colors"
              @click="handleDelete"
            >
              Remove stream
            </button>
            <span v-else />
            <button
              type="submit"
              :disabled="!url.trim() || testing"
              class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:bg-gray-400"
            >
              {{ submitLabel }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'

export default {
  name: 'StreamSourceModal',
  props: {
    source: {
      type: Object,
      default: null
    },
    existingUrls: {
      type: Array,
      default: () => []
    }
  },
  emits: ['close', 'add', 'save', 'delete'],
  setup(props, { emit }) {
    const urlInput = ref(null)
    const url = ref(props.source?.url || '')
    const label = ref(props.source?.label || '')
    const testing = ref(false)
    const error = ref('')
    const canForceSubmit = ref(false)

    const isEditing = computed(() => !!props.source)

    const submitLabel = computed(() => {
      if (testing.value) return 'Testing...'
      return isEditing.value ? 'Test & Save' : 'Test & Add'
    })

    const clearErrors = () => {
      error.value = ''
      canForceSubmit.value = false
    }

    const validate = () => {
      const trimmed = url.value.trim()
      if (!trimmed) {
        error.value = 'URL is required'
        return null
      }
      if (!trimmed.startsWith('rtsp://') && !trimmed.startsWith('rtsps://')) {
        error.value = 'Must start with rtsp:// or rtsps://'
        return null
      }
      // Check duplicates (exclude current URL in edit mode)
      const others = isEditing.value
        ? props.existingUrls.filter(u => u !== props.source.url)
        : props.existingUrls
      if (others.includes(trimmed)) {
        error.value = 'This URL is already added'
        return null
      }
      return trimmed
    }

    const testStream = async (streamUrl) => {
      testing.value = true
      try {
        const { data } = await api.post('/stream/test', {
          url: streamUrl,
          type: 'rtsp',
        })
        if (!data.success) {
          error.value = data.message || 'Stream not accessible'
          canForceSubmit.value = true
          return false
        }
        return true
      } catch {
        error.value = 'Test request failed'
        canForceSubmit.value = true
        return false
      } finally {
        testing.value = false
      }
    }

    const submitSource = (validatedUrl) => {
      const trimmedLabel = label.value.trim()
      if (isEditing.value) {
        emit('save', {
          url: validatedUrl,
          label: trimmedLabel,
          originalUrl: props.source.url,
        })
      } else {
        emit('add', { url: validatedUrl, label: trimmedLabel })
      }
    }

    const handleSubmit = async () => {
      clearErrors()
      const validatedUrl = validate()
      if (!validatedUrl) return

      const success = await testStream(validatedUrl)
      if (success) {
        submitSource(validatedUrl)
      }
    }

    const handleForceSubmit = () => {
      const validatedUrl = validate()
      if (!validatedUrl) return
      submitSource(validatedUrl)
    }

    const handleDelete = () => {
      emit('delete', props.source.url)
    }

    const handleBackdropClick = () => {
      if (!testing.value) {
        emit('close')
      }
    }

    onMounted(() => {
      if (urlInput.value) {
        urlInput.value.focus()
      }
    })

    return {
      urlInput,
      url,
      label,
      testing,
      error,
      canForceSubmit,
      isEditing,
      submitLabel,
      clearErrors,
      handleSubmit,
      handleForceSubmit,
      handleDelete,
      handleBackdropClick,
    }
  }
}
</script>
