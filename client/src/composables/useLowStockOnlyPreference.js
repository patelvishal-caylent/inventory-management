import { ref, watch } from 'vue'

const STORAGE_KEY = 'inventory-low-stock-only:v1'

// Missing, corrupt or unavailable storage falls back to off
const readLowStockOnly = () => {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY)) === true
  } catch {
    return false
  }
}

const writeLowStockOnly = (value) => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value === true))
  } catch {
    // Storage unavailable (private mode, quota, disabled); keep in-memory state only
  }
}

export function useLowStockOnlyPreference() {
  const lowStockOnly = ref(readLowStockOnly())

  watch(lowStockOnly, (value) => {
    writeLowStockOnly(value)
  }, { flush: 'sync' })

  return { lowStockOnly }
}
