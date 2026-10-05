<script setup lang="ts">
import type { Region } from '@/composables/useFestivals'
import { REGIONS } from '@/utils/festival'

defineProps<{ counts: Record<Region, number> }>()
const region = defineModel<Region | null>({ required: true })

// 대략적인 위치 배치: 경기·인천/서울/강원, 충청/경북·대구, 전라/경남·부산, 제주
const AREAS = `'gi se gw' 'cc cc gb' 'jl gn gn' 'jj . .'`

function tileClass(id: Region, count: number) {
  if (region.value === id) return 'border-ink bg-ink text-white'
  return count > 0 ? 'border-transparent text-ink' : 'border-line bg-bg text-[#6B6F77]'
}
</script>

<template>
  <section
    id="regions"
    aria-labelledby="regions-title"
    class="hidden min-w-0 flex-[1_1_340px] flex-col gap-3 rounded-[18px] md:flex border border-line bg-card p-4 md:gap-4 md:rounded-[20px] md:p-6"
  >
    <div>
      <h2 id="regions-title" class="text-[17px] font-bold md:mb-1 md:text-xl">지역별로 보기</h2>
      <p class="hidden text-sm text-sub md:block">지역을 누르면 목록이 바로 좁혀져요.</p>
    </div>
    <div
      class="grid grid-cols-3 grid-rows-[repeat(4,62px)] gap-1.5 md:grid-rows-[repeat(4,84px)] md:gap-2"
      :style="{ gridTemplateAreas: AREAS }"
    >
      <button
        v-for="r in REGIONS"
        :key="r.id"
        type="button"
        :aria-pressed="region === r.id"
        :aria-label="`${r.label} ${counts[r.id]}곳`"
        class="flex cursor-pointer items-center justify-between rounded-xl border px-2.5 text-left transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_8px_18px_-10px_rgb(22_24_29/0.35)] active:scale-[0.97] md:flex-col md:items-start md:rounded-[14px] md:p-3"
        :class="tileClass(r.id, counts[r.id])"
        :style="{
          gridArea: r.area,
          background: region !== r.id && counts[r.id] > 0 ? r.tint : undefined,
        }"
        @click="region = region === r.id ? null : r.id"
      >
        <span class="text-xs font-bold whitespace-nowrap md:text-sm">{{ r.label }}</span>
        <span class="font-display text-xl leading-none md:text-[28px]">{{ counts[r.id] }}</span>
      </button>
    </div>
    <p class="mt-auto hidden text-xs text-sub md:block">타일은 실제 지도가 아닌 대략적인 위치 배치예요.</p>
  </section>
</template>
