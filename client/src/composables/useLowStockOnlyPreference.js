import { ref, watch } from 'vue'

export const LOW_STOCK_ONLY_STORAGE_KEY = 'inventory-low-stock-only:v1'

// Accessing window.localStorage itself can throw (e.g. blocked storage), so every
// touch goes through try/catch and falls back to "off".
const readStoredValue = () => {
  try {
    const raw = window.localStorage.getItem(LOW_STOCK_ONLY_STORAGE_KEY)
    if (raw === null) return false
    return JSON.parse(raw) === true
  } catch {
    return false
  }
}

const writeStoredValue = (value) => {
  try {
    window.localStorage.setItem(LOW_STOCK_ONLY_STORAGE_KEY, JSON.stringify(value))
  } catch {
    // Storage unavailable or full: keep the in-memory state only
  }
}

export function useLowStockOnlyPreference() {
  const lowStockOnly = ref(readStoredValue())

  watch(lowStockOnly, (value) => writeStoredValue(value === true), { flush: 'sync' })

  return { lowStockOnly }
}
