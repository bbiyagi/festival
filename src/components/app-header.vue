<script setup lang="ts">
import logo from '@/assets/logo.svg'
import { useFavorites } from '@/stores/favorites'

defineEmits<{ openSaved: [] }>()
const favorites = useFavorites()
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-line bg-card md:static">
    <div
      class="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-4 px-5 py-2.5 md:px-[clamp(20px,5vw,64px)] md:py-[18px]"
    >
      <RouterLink to="/" class="flex min-h-11 items-center gap-2.5 text-ink no-underline">
        <img :src="logo" alt="" class="size-7 md:size-8" />
        <span class="font-display text-[21px] tracking-[0.5px] md:text-2xl">동네축제</span>
      </RouterLink>
      <nav aria-label="주요 메뉴" class="flex flex-wrap items-center gap-2">
        <a href="#overview" class="hidden px-3.5 py-2.5 text-[15px] font-bold text-ink no-underline md:inline">일정 한눈에</a>
        <a href="#list" class="hidden px-3.5 py-2.5 text-[15px] font-medium text-sub no-underline md:inline">축제 목록</a>
        <button
          type="button"
          class="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-line bg-card px-3.5 text-sm font-bold text-ink transition hover:border-ink active:scale-95 md:px-4 md:text-[15px]"
          :aria-label="`찜한 축제 ${favorites.items.length}개`"
          @click="$emit('openSaved')"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" :fill="favorites.items.length ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="text-accent">
            <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"></path>
          </svg>
          <span class="hidden md:inline">찜한 축제</span> {{ favorites.items.length }}
        </button>
      </nav>
    </div>
  </header>
</template>
