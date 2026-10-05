<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQueryRaw } from 'vue-router'
import AppHeader from '@/components/app-header.vue'
import FestivalCard from '@/components/festival-card.vue'
import RegionChips from '@/components/region-chips.vue'
import RegionTiles from '@/components/region-tiles.vue'
import ScheduleGantt from '@/components/schedule-gantt.vue'
import { useFestivals, type Kind, type Region } from '@/composables/useFestivals'
import { useGeolocation } from '@/composables/useGeolocation'
import { useIntros } from '@/composables/useIntros'
import { useFavorites } from '@/stores/favorites'
import { toIsoDate } from '@/utils/date'
import {
  matchesQuery,
  matchesWhen,
  md,
  REGION_BY_ID,
  REGIONS,
  SORTS,
  sortFestivals,
  toView,
  weekday,
  WHENS,
  KINDS,
  type SortKey,
  type When,
} from '@/utils/festival'

// 지도 코드는 지도 탭을 열 때만 받는다
const FestivalMap = defineAsyncComponent(() => import('@/components/festival-map.vue'))

type View = 'list' | 'map' | 'saved'
// 오늘부터 6주를 먼저 받고, 일정표를 끝까지 넘기면 4주씩 더 (최대 6개월: TourAPI 하루 호출 한도)
const FIRST_DAYS = 42
const MAX_DAYS = 182

const route = useRoute()
const router = useRouter()
const favorites = useFavorites()
const { position: here, state: geo, locate: locateMe } = useGeolocation()

// 언제·지역·정렬·보기·선택한 축제는 주소에 남긴다 (기본값은 생략)
function setQuery(patch: LocationQueryRaw) {
  router.replace({ query: { ...route.query, ...patch } })
}
const kind = computed<Kind | 'all'>({
  get: () => KINDS.find((k) => k.id === route.query.kind)?.id ?? 'all',
  set: (v) => setQuery({ kind: v === 'all' ? undefined : v, selected: undefined }),
})
const when = computed<When>({
  get: () => WHENS.find((w) => w.id === route.query.when)?.id ?? 'all',
  set: (v) => setQuery({ when: v === 'all' ? undefined : v, selected: undefined }),
})
const region = computed<Region | null>({
  get: () => {
    const r = route.query.region as Region
    return r in REGION_BY_ID ? r : null
  },
  set: (v) => setQuery({ region: v ?? undefined, selected: undefined }),
})
// 기본 정렬: 내 위치를 알면 가까운 순, 모르면 마감 임박순
const defaultSort = computed<SortKey>(() => (here.value ? 'near' : 'deadline'))
const sort = computed<SortKey>({
  get: () => SORTS.find((s) => s.id === route.query.sort)?.id ?? defaultSort.value,
  set: (v) => setQuery({ sort: v === defaultSort.value ? undefined : v }),
})
const view = computed<View>({
  get: () => {
    const v = route.query.view
    return v === 'map' || (v === 'saved' && favorites.enabled) ? v : 'list'
  },
  set: (v) => setQuery({ view: v === 'list' ? undefined : v }),
})
const selected = computed<string | null>({
  get: () => (typeof route.query.selected === 'string' ? route.query.selected : null),
  set: (v) => setQuery({ selected: v ?? undefined }),
})

const today = toIsoDate(new Date())
const { festivals, end: rangeEnd, loading, loadingMore, canLoadMore, error, reload, loadMore } = useFestivals(
  today,
  FIRST_DAYS,
  MAX_DAYS,
)

onMounted(() => {
  locateMe()
  favorites.load()
  window.addEventListener('keydown', focusSearchOnSlash)
})
onBeforeUnmount(() => window.removeEventListener('keydown', focusSearchOnSlash))

// ── 검색: 주소의 q와 입력창을 잇는다. 타자마다 주소를 바꾸지 않게 잠깐 기다린다 ──
const q = computed(() => (typeof route.query.q === 'string' ? route.query.q : ''))
const qInput = ref(q.value)
const searchEl = ref<HTMLInputElement>()
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(qInput, (v) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => setQuery({ q: v.trim() ? v.trim() : undefined, selected: undefined }), 200)
})
watch(q, (v) => v !== qInput.value.trim() && (qInput.value = v))
// '/' 키로 검색창 바로 가기 (입력 중일 때는 제외)
function focusSearchOnSlash(e: KeyboardEvent) {
  const t = e.target as HTMLElement
  if (e.key !== '/' || t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName)) return
  e.preventDefault()
  searchEl.value?.focus()
}

const views = computed(() => festivals.value.map((f) => toView(f, today, here.value)))
const searched = computed(() => views.value.filter((f) => matchesQuery(f, q.value)))
const inWhen = computed(() => searched.value.filter((f) => matchesWhen(f, when.value, today)))
// 무엇을: 축제 / 공연 / 전시·박람회 / 행사 (언제 필터를 거친 뒤 개수)
const kindCounts = computed(() =>
  Object.fromEntries(KINDS.map((k) => [k.id, k.id === 'all' ? inWhen.value.length : inWhen.value.filter((f) => f.kind === k.id).length])),
)
const inKind = computed(() => (kind.value === 'all' ? inWhen.value : inWhen.value.filter((f) => f.kind === kind.value)))
const counts = computed(
  () => Object.fromEntries(REGIONS.map((r) => [r.id, inKind.value.filter((f) => f.region === r.id).length])) as Record<Region, number>,
)
const list = computed(() =>
  sortFestivals(region.value ? inKind.value.filter((f) => f.region === region.value) : inKind.value, sort.value),
)
// 찜 목록은 기간·지역 필터와 상관없이 전부, 시작일순 (끝난 축제는 뒤로)
const savedList = computed(() =>
  sortFestivals(
    favorites.items.map((f) => toView(f, today, here.value)),
    'start',
  ),
)
const ready = computed(() => !loading.value && !error.value)
// 필터가 바뀌면 일정표·카드 등장 애니메이션을 다시 재생
const animKey = computed(() => `${q.value}-${when.value}-${kind.value}-${region.value}-${sort.value}`)

const WHEN_INDEX = computed(() => WHENS.findIndex((w) => w.id === when.value))
const TABS = computed<{ id: View; label: string; count?: number }[]>(() => [
  { id: 'list', label: '목록' },
  { id: 'map', label: '지도로 보기' },
  { id: 'saved', label: '찜한 축제', count: favorites.items.length },
])

const rangeLabel = computed(() => `${md(today)} ${weekday(today)} – ${md(rangeEnd.value)} ${weekday(rangeEnd.value)}`)
const regionLabel = computed(() => (region.value ? REGION_BY_ID[region.value].label : '전국'))
const heroTitle = computed(() => (here.value ? '가까운 축제부터,\n어디로 떠나볼까요?' : '다가오는 축제,\n어디로 떠나볼까요?'))

// 찜한 축제는 기능이 열리기 전까지 안내 토스트만
function openView(v: View) {
  if (v === 'saved' && !favorites.enabled) return favorites.notReady()
  view.value = v
}

function locate(id: string) {
  setQuery({ view: 'map', selected: id })
  window.scrollTo({ top: document.getElementById('view-tabs')?.offsetTop ?? 0, behavior: 'smooth' })
}

// ponytail: 카드는 24개씩 더 보기. 수백 건이 흔해지면 무한 스크롤로.
const PAGE = 24
const shown = ref(PAGE)
watch(list, () => (shown.value = PAGE))

// 화면에 보이는 카드만 운영 시간·무료 여부를 받아 온다 (축제당 TourAPI 1회, 서버 1시간 캐시)
const { want: wantIntros } = useIntros()
watch(
  () => (view.value === 'saved' ? savedList.value : view.value === 'list' ? list.value.slice(0, shown.value) : []).map((f) => f.id),
  (ids) => ids.length && wantIntros(ids),
  { immediate: true },
)

// 찜 저장 오류는 잠깐 띄웠다가 닫는다
let toastTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => favorites.error,
  (e) => {
    clearTimeout(toastTimer)
    if (e) toastTimer = setTimeout(() => (favorites.error = null), 6000)
  },
)
</script>

<template>
  <AppHeader @open-saved="openView('saved')" />
  <main class="mx-auto max-w-[1280px] px-3 pb-10 md:px-[clamp(20px,5vw,64px)] md:pb-20">
    <!-- 제목 + 언제 갈까요? -->
    <section
      aria-labelledby="hero-title"
      class="flex flex-col gap-5 px-2 pt-7 pb-4 md:flex-row md:flex-wrap md:items-end md:justify-between md:gap-7 md:px-0 md:pt-14 md:pb-8"
    >
      <div class="flex min-w-0 flex-col gap-2.5 md:gap-3.5">
        <p class="text-[13px] font-bold text-accent md:text-[15px]" aria-live="polite">
          {{ rangeLabel }} &nbsp;·&nbsp; {{ regionLabel }} {{ ready ? `${list.length}곳` : '…' }}
        </p>
        <Transition mode="out-in" enter-from-class="opacity-0 translate-y-2" leave-to-class="opacity-0 -translate-y-2">
          <h1
            id="hero-title"
            :key="heroTitle"
            class="font-display text-[32px] leading-[1.2] font-normal whitespace-pre-line transition duration-300 md:min-h-[2.3em] md:text-[clamp(40px,5vw,60px)] md:leading-[1.15]"
          >
            {{ heroTitle }}
          </h1>
        </Transition>
        <!-- 내 위치 상태 -->
        <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-sub md:text-[15px]" aria-live="polite">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" :class="geo === 'ok' ? 'text-[#1D4ED8]' : ''">
            <circle cx="12" cy="12" r="4"></circle>
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3"></path>
          </svg>
          <template v-if="geo === 'locating' || geo === 'idle'">내 위치를 찾는 중…</template>
          <template v-else-if="geo === 'ok'">내 위치에서 가까운 축제부터 보여 드려요.</template>
          <template v-else>
            {{ geo === 'denied' ? '위치 권한이 없어서' : '위치를 알 수 없어서' }} 마감 임박순으로 보여 드려요.
            <button type="button" class="min-h-11 cursor-pointer font-bold text-ink underline underline-offset-4 hover:text-accent" @click="locateMe">
              내 위치 다시 찾기
            </button>
          </template>
        </p>
      </div>

      <!-- 언제 갈까요?: 선택 배경이 미끄러진다 -->
      <div class="flex flex-col gap-2">
        <span id="when-label" class="text-sm font-bold text-sub">언제 갈까요?</span>
        <div role="group" aria-labelledby="when-label" class="relative grid grid-cols-4 rounded-full border border-line bg-card p-1">
          <span
            class="absolute top-1 bottom-1 left-1 w-[calc((100%-8px)/4)] rounded-full bg-accent shadow-[0_4px_12px_-4px_rgb(194_65_12/0.6)] transition-transform duration-300 ease-out"
            :style="{ transform: `translateX(${WHEN_INDEX * 100}%)` }"
            aria-hidden="true"
          ></span>
          <button
            v-for="w in WHENS"
            :key="w.id"
            type="button"
            :aria-pressed="when === w.id"
            class="relative min-h-11 cursor-pointer rounded-full px-1 text-[13px] font-bold whitespace-nowrap transition-colors duration-300 active:scale-95 md:min-h-12 md:px-5 md:text-[15px]"
            :class="when === w.id ? 'text-white' : 'text-ink hover:text-accent'"
            @click="when = w.id"
          >
            {{ w.label }}
          </button>
        </div>
      </div>
    </section>

    <!-- 검색 + 무엇을 볼까요?(분류) -->
    <div v-if="view !== 'saved'" class="mb-3 flex flex-col gap-3 md:mb-4 md:flex-row-reverse md:items-center md:justify-between">
      <div role="search" class="relative md:w-80">
        <label for="festival-search" class="sr-only">축제 검색</label>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true" class="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-sub">
          <circle cx="11" cy="11" r="7"></circle>
          <path d="m20 20-3.5-3.5"></path>
        </svg>
        <input
          id="festival-search"
          ref="searchEl"
          v-model="qInput"
          type="search"
          enterkeyhint="search"
          autocomplete="off"
          placeholder="축제 이름, 지역, 분류로 찾기"
          class="min-h-11 w-full rounded-full border border-line bg-card pr-11 pl-10 text-[15px] text-ink transition outline-none placeholder:text-[#8A8E96] hover:border-[#C9C6BD] focus:border-ink focus:ring-4 focus:ring-ink/5 [&::-webkit-search-cancel-button]:hidden"
          @keydown.esc="qInput = ''"
        />
        <button
          v-if="qInput"
          type="button"
          aria-label="검색어 지우기"
          class="absolute top-1/2 right-1.5 flex size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full text-sub transition hover:bg-bg hover:text-ink"
          @click="qInput = ''; searchEl?.focus()"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12"></path>
          </svg>
        </button>
        <kbd v-else class="pointer-events-none absolute top-1/2 right-3.5 hidden -translate-y-1/2 rounded border border-line px-1.5 text-xs text-sub md:block">/</kbd>
      </div>
    <div role="group" aria-label="분류" class="-mx-3 flex gap-1.5 overflow-x-auto px-5 whitespace-nowrap md:mx-0 md:flex-wrap md:px-0">
      <button
        v-for="k in KINDS"
        :key="k.id"
        type="button"
        :aria-pressed="kind === k.id"
        class="inline-flex min-h-9 flex-none cursor-pointer items-center gap-1 rounded-lg px-3 text-sm font-bold transition duration-200 active:scale-95"
        :class="kind === k.id ? 'bg-accent text-white' : 'bg-[#ECEAE4] text-ink hover:bg-[#E3E0D8]'"
        @click="kind = k.id"
      >
        {{ k.label }}<span class="text-xs font-medium opacity-75">{{ kindCounts[k.id] }}</span>
      </button>
    </div>
    </div>

    <!-- 지역 칩 + 정렬(PC) -->
    <div v-if="view !== 'saved'" class="flex items-center gap-2 pb-5 md:pb-8">
      <RegionChips v-model="region" :counts="counts" :total="inKind.length" class="min-w-0 flex-1" />
      <label class="hidden flex-none items-center gap-2 text-sm text-sub md:inline-flex">
        정렬
        <select v-model="sort" class="min-h-11 cursor-pointer rounded-[10px] border border-line bg-card px-3 text-[15px] text-ink transition hover:border-ink">
          <option v-for="s in SORTS" :key="s.id" :value="s.id">{{ s.label }}</option>
        </select>
      </label>
    </div>

    <!-- 목록 / 지도로 보기 / 찜한 축제 탭 -->
    <div id="view-tabs" role="tablist" aria-label="보기 방식" class="relative mb-5 flex scroll-mt-20 gap-1 border-b border-line md:mb-6">
      <button
        v-for="t in TABS"
        :key="t.id"
        type="button"
        role="tab"
        :aria-selected="view === t.id"
        :aria-controls="`panel-${t.id}`"
        class="relative inline-flex min-h-12 flex-none cursor-pointer items-center gap-2 px-3 text-[15px] font-bold transition-colors md:px-4 md:text-base"
        :class="view === t.id ? 'text-ink' : 'text-sub hover:text-ink'"
        @click="openView(t.id)"
      >
        <svg v-if="t.id === 'list'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"></path>
        </svg>
        <svg v-else-if="t.id === 'map'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14"></path>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"></path>
        </svg>
        {{ t.label }}
        <span v-if="t.count" :key="t.count" class="animate-[heart-pop_0.35s_ease-out] rounded-full bg-accent px-2 py-0.5 text-xs text-white">{{ t.count }}</span>
        <span
          class="absolute inset-x-2 -bottom-px h-[3px] origin-center rounded-full bg-accent transition-transform duration-300 ease-out"
          :class="view === t.id ? 'scale-x-100' : 'scale-x-0'"
          aria-hidden="true"
        ></span>
      </button>
    </div>

    <!-- 찜한 축제: 축제 API와 상관없이 저장해 둔 정보로 그린다 -->
    <section v-if="view === 'saved'" id="panel-saved" role="tabpanel" aria-label="찜한 축제" class="animate-fade-up">
      <ul v-if="savedList.length" class="flex flex-col gap-2.5 md:grid md:grid-cols-[repeat(auto-fill,minmax(260px,1fr))] md:gap-5">
        <li v-for="(f, i) in savedList" :key="f.id" class="animate-fade-up" :style="{ animationDelay: `${i * 30}ms` }">
          <FestivalCard :festival="f" class="h-full" @locate="locate(f.id)" />
        </li>
      </ul>
      <div v-else class="flex min-h-60 flex-col items-center justify-center gap-2 rounded-[20px] border border-dashed border-line p-8 text-center">
        <p class="font-bold">아직 찜한 축제가 없어요.</p>
        <p class="text-sm text-sub">축제 카드의 하트를 누르면 여기에 모여요. 로그인 없이 이 기기에 저장돼요.</p>
      </div>
    </section>

    <!-- 불러오는 중 / 오류 -->
    <div
      v-else-if="!ready"
      class="flex min-h-60 flex-col items-center justify-center gap-3 rounded-[20px] border border-line bg-card p-8 text-center"
      :aria-busy="loading"
      role="status"
    >
      <template v-if="loading">
        <span class="size-6 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true"></span>
        <p class="text-sub">축제 정보를 불러오는 중…</p>
      </template>
      <template v-else>
        <p class="font-bold">축제 정보를 불러오지 못했어요.</p>
        <p class="text-sm text-sub">{{ error?.message }}</p>
        <button type="button" class="min-h-11 cursor-pointer rounded-full bg-ink px-6 font-bold text-white transition active:scale-95" @click="reload">
          다시 시도
        </button>
      </template>
    </div>

    <!-- 지도로 보기 -->
    <div v-else-if="view === 'map'" id="panel-map" role="tabpanel" class="animate-fade-up">
      <FestivalMap v-model:selected="selected" :list="list" :here="here" />
    </div>

    <!-- 목록 -->
    <div v-else id="panel-list" role="tabpanel">
      <!-- 일정 한눈에 + 지역별로 보기 -->
      <div class="flex flex-wrap items-stretch gap-4 md:gap-6">
        <ScheduleGantt
          :key="animKey"
          :list="list"
          :start="today"
          :end="rangeEnd"
          :today="today"
          :loading-more="loadingMore"
          :can-load-more="canLoadMore"
          @load-more="loadMore"
        />
        <RegionTiles v-model="region" :counts="counts" />
      </div>

      <!-- 축제 목록 -->
      <section id="list" aria-labelledby="list-title" class="scroll-mt-4 pt-7 md:pt-14">
        <div class="mb-3 flex flex-wrap items-baseline justify-between gap-3 px-2 md:mb-5 md:px-0">
          <h2 id="list-title" class="text-[19px] font-bold md:text-2xl">
            {{ kind === 'all' ? '전체' : KINDS.find((k) => k.id === kind)?.label }} 목록 <span class="text-accent">{{ list.length }}</span>
          </h2>
          <label class="text-[13px] text-sub md:hidden">
            <span class="sr-only">정렬</span>
            <select v-model="sort" class="min-h-11 rounded-[10px] border border-line bg-card px-2 text-sm text-ink">
              <option v-for="s in SORTS" :key="s.id" :value="s.id">{{ s.label }}</option>
            </select>
          </label>
          <span class="hidden text-sm text-sub md:inline">{{ SORTS.find((s) => s.id === sort)?.label }}</span>
        </div>

        <ul :key="animKey" class="flex flex-col gap-2.5 md:grid md:grid-cols-[repeat(auto-fill,minmax(260px,1fr))] md:gap-5">
          <li
            v-for="(f, i) in list.slice(0, shown)"
            :key="f.id"
            class="animate-fade-up"
            :style="{ animationDelay: `${(i % PAGE) * 30}ms` }"
          >
            <FestivalCard :festival="f" class="h-full" @locate="locate(f.id)" />
          </li>
        </ul>
        <button
          v-if="list.length > shown"
          type="button"
          class="mx-auto mt-6 flex min-h-11 cursor-pointer items-center rounded-full border border-line bg-card px-6 font-bold transition hover:border-ink hover:shadow-sm active:scale-95"
          @click="shown += PAGE"
        >
          더 보기 ({{ list.length - shown }}개 남음)
        </button>
        <p v-if="list.length === 0" class="py-12 text-center text-sub">
          <template v-if="q">‘{{ q }}’에 맞는 축제가 없어요. 다른 이름이나 지역으로 찾아보세요.</template>
          <template v-else>다른 지역이나 날짜를 선택해 보세요.</template>
        </p>
      </section>
    </div>

    <p class="mx-2 mt-7 text-[11px] text-sub md:mx-0 md:mt-16 md:text-xs">
      축제 정보: 한국관광공사 TourAPI · 지도: NAVER · 일정은 주최 측 사정으로 바뀔 수 있어요.
    </p>
  </main>

  <!-- 찜 저장 오류 알림 -->
  <Transition enter-from-class="opacity-0 translate-y-4" leave-to-class="opacity-0 translate-y-4">
    <div
      v-if="favorites.error"
      role="alert"
      class="fixed inset-x-3 bottom-4 z-20 mx-auto flex max-w-md items-center gap-3 rounded-2xl bg-ink px-4 py-3 text-sm text-white shadow-lg transition duration-300"
    >
      <span class="flex-1">{{ favorites.error }}</span>
      <button type="button" aria-label="알림 닫기" class="flex size-9 flex-none cursor-pointer items-center justify-center rounded-full hover:bg-white/10" @click="favorites.error = null">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
          <path d="M18 6 6 18M6 6l12 12"></path>
        </svg>
      </button>
    </div>
  </Transition>
</template>
