<script setup lang="ts">
import type { Region } from '@/composables/useFestivals'
import { REGIONS } from '@/utils/festival'

defineProps<{ counts: Record<Region, number>; total: number }>()
const region = defineModel<Region | null>({ required: true })

const chips = [{ id: null, label: '전국' }, ...REGIONS] as const
</script>

<template>
  <div
    role="group"
    aria-label="지역 필터"
    class="-mx-3 flex gap-2 overflow-x-auto px-5 whitespace-nowrap md:mx-0 md:flex-wrap md:overflow-visible md:px-0"
  >
    <button
      v-for="c in chips"
      :key="c.id ?? 'all'"
      type="button"
      :aria-pressed="region === c.id"
      class="inline-flex min-h-10 flex-none cursor-pointer items-center gap-1.5 rounded-full border px-3.5 text-sm font-medium transition duration-200 active:scale-95 md:min-h-11 md:px-4 md:text-[15px]"
      :class="region === c.id ? 'border-ink bg-ink text-white' : 'border-line bg-card text-ink hover:border-ink'"
      @click="region = c.id"
    >
      {{ c.label }}<span class="text-xs opacity-70 md:text-[13px]">{{ c.id ? counts[c.id] : total }}</span>
    </button>
  </div>
</template>
