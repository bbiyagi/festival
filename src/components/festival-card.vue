<script setup lang="ts">
import { ref } from 'vue'
import { openFestivalSite } from '@/utils/open-site'
import { useIntros } from '@/composables/useIntros'
import { useFavorites } from '@/stores/favorites'
import { formatDistance, type FestivalView, type Status } from '@/utils/festival'

defineProps<{ festival: FestivalView }>()
defineEmits<{ locate: [] }>()
const favorites = useFavorites()
const { intros } = useIntros()

// 사진이 없거나 못 불러오면 권역 색 + 지명 자리표시
const imageFailed = ref(false)

const BADGE: Record<Status, string> = {
  ongoing: 'bg-accent text-white',
  upcoming: 'bg-upcoming text-white',
  always: 'bg-sub text-white',
  ended: 'bg-[#D6D3CB] text-ink',
}
const ICON_BTN =
  'flex size-11 cursor-pointer items-center justify-center rounded-full transition hover:scale-110 active:scale-90'
</script>

<template>
  <article
    class="group relative flex items-center gap-3 rounded-2xl border border-line bg-card p-2.5 transition duration-300 ease-out hover:-translate-y-1 hover:border-[#D3D0C7] hover:shadow-[0_12px_28px_-12px_rgb(22_24_29/0.25)] md:flex-col md:items-stretch md:gap-0 md:overflow-hidden md:rounded-[18px] md:p-0"
    :class="{ 'opacity-60 hover:opacity-100': festival.status === 'ended' }"
  >
    <div
      class="relative flex size-[88px] flex-none items-end overflow-hidden rounded-xl p-2 md:h-[168px] md:w-auto md:rounded-none md:p-3.5"
      :style="{ background: festival.tint }"
    >
      <!-- 모바일 88px 썸네일은 작은 사진, PC 카드는 큰 사진 -->
      <picture v-if="festival.image && !imageFailed">
        <source media="(min-width: 768px)" :srcset="festival.image" />
        <img
          :src="festival.thumb ?? festival.image"
          alt=""
          loading="lazy"
          decoding="async"
          class="absolute inset-0 size-full object-cover transition duration-500 ease-out group-hover:scale-105"
          @error="imageFailed = true"
        />
      </picture>
      <span v-else class="font-display text-lg text-ink opacity-85 md:text-[34px]" aria-hidden="true">{{
        festival.town
      }}</span>
      <div class="absolute bottom-3 left-3 hidden gap-1.5 md:flex">
        <span v-if="festival.category" class="rounded-full bg-ink/70 px-2.5 py-1 text-xs font-bold text-white backdrop-blur-sm">{{
          festival.category
        }}</span>
        <span
          v-if="intros.get(festival.id)?.price === 'free'"
          class="animate-fade-up rounded-full bg-[#E3F1E7] px-2.5 py-1 text-xs font-bold text-[#1E6B3A]"
          >무료</span
        >
      </div>
      <div class="absolute top-1.5 left-1.5 flex gap-1.5 md:top-3 md:left-3">
        <span class="rounded-full px-[7px] py-0.5 text-[10px] font-bold md:px-2.5 md:py-1 md:text-xs" :class="BADGE[festival.status]">{{
          festival.statusLabel
        }}</span>
        <span
          class="hidden rounded-full bg-card px-2.5 py-1 text-xs font-bold md:inline"
          :class="festival.urgent ? 'text-accent' : 'text-ink'"
          >{{ festival.dday }}</span
        >
        <!-- 모바일: 상태 옆 (PC는 사진 왼쪽 아래, 오른쪽 위 버튼과 겹치지 않게) -->
        <span
          v-if="intros.get(festival.id)?.price === 'free'"
          class="animate-fade-up rounded-full bg-[#E3F1E7] px-[7px] py-0.5 text-[10px] font-bold text-[#1E6B3A] md:hidden"
          >무료</span
        >
      </div>
    </div>

    <div class="flex min-w-0 flex-1 flex-col gap-[3px] md:gap-1.5 md:px-[18px] md:pt-4 md:pb-[18px]">
      <span class="text-xs font-bold text-accent md:text-[13px]">
        <span v-if="festival.category" class="text-sub md:hidden">{{ festival.category }} · </span>{{ festival.place }}
        <span v-if="festival.distanceKm !== null" class="font-medium text-sub">· {{ formatDistance(festival.distanceKm) }}</span>
      </span>
      <h3 class="text-[15px] leading-[1.35] font-bold md:text-lg">
        <!-- 카드 전체를 누르면 홈페이지를 새 탭으로 (::after가 카드를 덮는다) -->
        <button
          type="button"
          class="cursor-pointer text-left after:absolute after:inset-0 after:rounded-[inherit] after:content-[''] focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-accent"
          :aria-label="`${festival.title} 홈페이지 새 탭에서 열기`"
          @click="openFestivalSite(festival)"
        >
          {{ festival.title }}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="ml-0.5 inline align-[-1px] text-sub opacity-0 transition group-hover:opacity-100">
            <path d="M7 17 17 7M8 7h9v9"></path>
          </svg>
        </button>
      </h3>
      <span class="text-xs text-sub md:hidden">
        {{ festival.range }}
        <b :class="festival.urgent ? 'text-accent' : 'text-ink'">{{ festival.dday }}</b>
      </span>
      <span class="hidden items-center gap-1.5 text-sm text-sub md:inline-flex">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="18" height="18" rx="2"></rect>
          <path d="M16 2v4M8 2v4M3 10h18"></path>
        </svg>
        {{ festival.rangeLong }}
      </span>
      <span v-if="intros.get(festival.id)?.playtime" class="flex animate-fade-up items-start gap-1.5 text-xs text-sub md:text-sm">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true" class="mt-0.5 flex-none md:mt-[3px]">
          <circle cx="12" cy="12" r="9"></circle>
          <path d="M12 7v5l3 2"></path>
        </svg>
        <span class="sr-only">운영 시간</span><span class="line-clamp-1">{{ intros.get(festival.id)?.playtime }}</span>
      </span>
    </div>

    <!-- 찜 · 지도: PC는 사진 오른쪽 위, 모바일은 행 오른쪽 끝에 세로로 (카드 링크 위에 올라온다) -->
    <div class="relative z-10 flex flex-none flex-col md:absolute md:top-2 md:right-2 md:flex-row md:gap-1.5">
      <button
        type="button"
        :aria-label="favorites.has(festival.id) ? `${festival.title} 찜 해제` : `${festival.title} 찜하기`"
        :aria-pressed="favorites.has(festival.id)"
        :class="[ICON_BTN, 'text-accent md:bg-card md:shadow-sm']"
        @click="favorites.toggle(festival)"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          :fill="favorites.has(festival.id) ? 'currentColor' : 'none'"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          :class="{ 'animate-[heart-pop_0.35s_ease-out]': favorites.has(festival.id) }"
        >
          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"></path>
        </svg>
      </button>
      <button
        v-if="festival.lat !== null"
        type="button"
        :aria-label="`${festival.title} 지도에서 보기`"
        :class="[ICON_BTN, 'text-ink hover:text-accent md:bg-card md:shadow-sm']"
        @click="$emit('locate')"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"></path>
          <circle cx="12" cy="10" r="3"></circle>
        </svg>
      </button>
    </div>
  </article>
</template>
