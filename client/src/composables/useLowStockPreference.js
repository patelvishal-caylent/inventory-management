// Persists the Inventory "Low stock only" toggle in localStorage.
// Storage may be missing, blocked or throw, so every access is guarded and
// failures fall back to "off" / are swallowed.
export const LOW_STOCK_STORAGE_KEY = 'inventory-low-stock-only:v1'

export function readLowStockOnly() {
  try {
    return window.localStorage.getItem(LOW_STOCK_STORAGE_KEY) === 'true'
  } catch (err) {
    return false
  }
}

export function writeLowStockOnly(value) {
  try {
    window.localStorage.setItem(LOW_STOCK_STORAGE_KEY, value ? 'true' : 'false')
  } catch (err) {
    // Ignore: the toggle still works in memory for this session
  }
}
