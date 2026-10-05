<script setup lang="ts">
import { computed } from 'vue'
import type { Region } from '@/composables/useFestivals'
import { REGIONS } from '@/utils/festival'

const props = defineProps<{ counts: Record<Region, number>; total: number; mine: Region | null }>()
const region = defineModel<Region | null>({ required: true })

// 전국 → 내 위치 지역(📍) → 나머지
const chips = computed(() => {
  const mine = REGIONS.find((r) => r.id === props.mine)
  return [{ id: null, label: '전국' }, ...(mine ? [mine] : []), ...REGIONS.filter((r) => r !== mine)]
})
</script>

<template>
  <div
    role="group"
    aria-label="지역 필터"
    class="-mx-3 flex gap-2 overflow-x-auto px-5 whitespace-nowrap [scrollbar-width:none] md:mx-0 md:flex-wrap md:overflow-visible md:px-0"
  >
    <button
      v-for="c in chips"
      :key="c.id ?? 'all'"
      type="button"
      :aria-pressed="region === c.id"
      :aria-label="c.id && c.id === mine ? `내 위치 지역 ${c.label}` : undefined"
      class="inline-flex min-h-10 flex-none cursor-pointer items-center gap-1.5 rounded-full border px-3.5 text-sm font-medium transition duration-200 active:scale-95 md:min-h-11 md:px-4 md:text-[15px]"
      :class="region === c.id ? 'border-ink bg-ink text-white' : 'border-line bg-card text-ink hover:border-ink'"
      @click="region = c.id"
    >
      <svg v-if="c.id && c.id === mine" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" :class="region === c.id ? 'text-white' : 'text-[#1D4ED8]'">
        <path d="M12 2a8 8 0 0 0-8 8c0 6 8 12 8 12s8-6 8-12a8 8 0 0 0-8-8zm0 11a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"></path>
      </svg>
      {{ c.label }}<span class="text-xs opacity-70 md:text-[13px]">{{ c.id ? counts[c.id] : total }}</span>
    </button>
  </div>
</template>
