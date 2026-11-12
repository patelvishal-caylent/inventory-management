// Persists the Inventory "Low stock only" toggle in localStorage.
// Storage may be missing, blocked or throw, so every access is guarded and
// failures fall back to "off" / are swallowed.
export const LOW_STOCK_STORAGE_KEY = 'inventory-low-stock-only:v1'

/**
 * Read the persisted "Low stock only" preference.
 * @returns {boolean} true only when the stored value is exactly 'true';
 *   missing, corrupt or inaccessible storage returns false.
 */
export function readLowStockOnly() {
  try {
    return window.localStorage.getItem(LOW_STOCK_STORAGE_KEY) === 'true'
  } catch (err) {
    return false
  }
}

/**
 * Persist the "Low stock only" preference as 'true' or 'false'.
 * Storage errors are swallowed so the toggle keeps working in memory.
 * @param {boolean} value - the current toggle state
 * @returns {void}
 */
export function writeLowStockOnly(value) {
  try {
    window.localStorage.setItem(LOW_STOCK_STORAGE_KEY, value ? 'true' : 'false')
  } catch (err) {
    // Ignore: the toggle still works in memory for this session
  }
}
