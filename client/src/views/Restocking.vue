<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetTitle') }}</h3>
        </div>
        <div class="budget-control">
          <div class="budget-value">{{ formatMoney(budget) }}</div>
          <input
            type="range"
            v-model.number="budget"
            min="0"
            :max="sliderMax"
            step="5000"
            class="budget-slider"
            :aria-label="t('restocking.budgetTitle')"
          >
          <div class="budget-scale">
            <span>{{ formatMoney(0) }}</span>
            <span>{{ formatMoney(sliderMax) }}</span>
          </div>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.itemsSelected') }}</div>
          <div class="stat-value">{{ selectedItems.length }} / {{ candidates.length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ formatMoney(totalCost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.budgetRemaining') }}</div>
          <div class="stat-value">{{ formatMoney(budgetRemaining) }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('restocking.uncoveredCost') }}</div>
          <div class="stat-value">{{ formatMoney(uncoveredCost) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
          <button
            class="place-order-btn"
            :disabled="submitting || selectedItems.length === 0"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="successMessage" class="submit-success">{{ successMessage }}</div>
        <div v-if="submitError" class="error">{{ submitError }}</div>

        <div v-if="candidates.length === 0" class="no-recommendations">
          {{ t('restocking.noShortages') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.onHand') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.shortage') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.included') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in candidates"
                :key="item.sku"
                :class="{ 'row-excluded': !isSelected(item.sku) }"
              >
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ item.quantity_on_hand }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td><strong>{{ item.shortage }}</strong></td>
                <td>{{ formatUnitCost(item.unit_cost) }}</td>
                <td>{{ formatMoney(item.cost) }}</td>
                <td>
                  <span v-if="isSelected(item.sku)" class="badge success">{{ t('restocking.included') }}</span>
                  <span v-else class="badge warning">{{ t('restocking.overBudget') }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const allForecasts = ref([])
    const inventoryItems = ref([])
    const budget = ref(100000)

    const submitting = ref(false)
    const submitError = ref(null)
    const successMessage = ref(null)

    const formatMoney = (v) => formatCurrency(v, currentCurrency.value)
    const formatUnitCost = (v) => formatCurrencyWithDecimals(v, currentCurrency.value, 2)

    const inventoryBySku = computed(() => {
      const map = new Map()
      for (const item of inventoryItems.value) map.set(item.sku, item)
      return map
    })

    const candidates = computed(() => {
      const rows = []
      for (const f of allForecasts.value) {
        const inv = inventoryBySku.value.get(f.item_sku)
        if (!inv) continue
        const shortage = f.forecasted_demand - inv.quantity_on_hand
        if (shortage <= 0) continue
        rows.push({
          sku: inv.sku,
          name: inv.name,
          category: inv.category,
          unit_cost: inv.unit_cost,
          quantity_on_hand: inv.quantity_on_hand,
          forecasted_demand: f.forecasted_demand,
          shortage,
          cost: shortage * inv.unit_cost
        })
      }
      return rows.sort((a, b) => b.shortage - a.shortage || a.sku.localeCompare(b.sku))
    })

    const totalShortageCost = computed(() => candidates.value.reduce((s, c) => s + c.cost, 0))

    const sliderMax = computed(() => Math.max(50000, Math.ceil(totalShortageCost.value / 10000) * 10000))

    const selection = computed(() => {
      let spent = 0
      const selectedSkus = new Set()
      for (const c of candidates.value) {
        if (spent + c.cost <= budget.value) {
          selectedSkus.add(c.sku)
          spent += c.cost
        }
      }
      return { selectedSkus, totalCost: spent }
    })

    const selectedItems = computed(() => candidates.value.filter(c => selection.value.selectedSkus.has(c.sku)))
    const totalCost = computed(() => selection.value.totalCost)
    const budgetRemaining = computed(() => Math.max(0, budget.value - totalCost.value))
    const uncoveredCost = computed(() => totalShortageCost.value - totalCost.value)
    const isSelected = (sku) => selection.value.selectedSkus.has(sku)

    const loadRestockData = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const [forecastsData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory({ warehouse: filters.warehouse, category: filters.category })
        ])
        allForecasts.value = forecastsData
        inventoryItems.value = inventoryData
      } catch (err) {
        error.value = 'Failed to load restock data: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      return date.toLocaleDateString(currentLocale.value)
    }

    const placeOrder = async () => {
      try {
        submitting.value = true
        submitError.value = null
        successMessage.value = null
        const created = await api.createRestockOrder({
          budget: budget.value,
          items: selectedItems.value.map(i => ({
            sku: i.sku,
            name: i.name,
            category: i.category,
            quantity: i.shortage,
            unit_cost: i.unit_cost
          }))
        })
        successMessage.value = t('restocking.orderPlaced', {
          orderNumber: created.order_number,
          expectedDelivery: formatDate(created.expected_delivery)
        })
      } catch (err) {
        submitError.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => { loadRestockData() })
    watch(budget, () => { successMessage.value = null; submitError.value = null })

    // Narrowing the filters shrinks sliderMax, which can leave budget stranded above
    // the track's right edge - the readout would then disagree with the thumb position
    watch(sliderMax, (max) => {
      if (budget.value > max) {
        budget.value = max
      }
    })

    onMounted(loadRestockData)

    return {
      t,
      loading,
      error,
      budget,
      candidates,
      sliderMax,
      selectedItems,
      totalCost,
      budgetRemaining,
      uncoveredCost,
      isSelected,
      submitting,
      submitError,
      successMessage,
      placeOrder,
      formatMoney,
      formatUnitCost,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-control {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.budget-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  cursor: pointer;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  cursor: pointer;
}

.budget-slider:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-success {
  background: #d1fae5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.938rem;
}

.row-excluded {
  opacity: 0.5;
}

.no-recommendations {
  text-align: center;
  padding: 3rem;
  color: #64748b;
}
</style>
