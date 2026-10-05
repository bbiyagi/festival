<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { addDays, barSpan, dayCells, md, type FestivalView, type Status } from '@/utils/festival'
import { openFestivalSite } from '@/utils/open-site'

const props = defineProps<{
  list: FestivalView[]
  start: string // 오늘
  end: string // 지금까지 불러온 마지막 날
  today: string
  loadingMore: boolean
  canLoadMore: boolean
}>()
const emit = defineEmits<{ loadMore: [] }>()

// 하루 칸 너비와 왼쪽 이름 칸 (PC만). 모바일은 이름이 막대 위 줄에 온다.
const wide = ref(false)
const mq = window.matchMedia('(min-width: 768px)')
const syncWide = () => (wide.value = mq.matches)
syncWide()
mq.addEventListener('change', syncWide)
onBeforeUnmount(() => mq.removeEventListener('change', syncWide))
const DAY_W = computed(() => (wide.value ? 40 : 32))
const NAME_W = computed(() => (wide.value ? 220 : 0))

const days = computed(() => dayCells(props.start, props.end, props.today))
const trackW = computed(() => days.value.length * DAY_W.value)
const todayIdx = computed(() => days.value.findIndex((d) => d.isToday))

// ── 끌어서 넘기기: 마우스는 직접 끌기, 터치·트랙패드는 기본 가로 스크롤 ──
const scroller = ref<HTMLDivElement>()
const dragging = ref(false)
let drag: { x: number; left: number; moved: boolean } | null = null

function onPointerDown(e: PointerEvent) {
  if (e.pointerType !== 'mouse' || e.button !== 0 || !scroller.value) return
  drag = { x: e.clientX, left: scroller.value.scrollLeft, moved: false }
}
function onPointerMove(e: PointerEvent) {
  if (!drag || !scroller.value) return
  const dx = e.clientX - drag.x
  if (!drag.moved && Math.abs(dx) < 4) return
  if (!drag.moved) {
    drag.moved = true
    dragging.value = true
    scroller.value.setPointerCapture(e.pointerId)
  }
  scroller.value.scrollLeft = drag.left - dx
}
function onPointerUp() {
  // 끌기가 끝나며 생기는 클릭은 무시한다 (끌다가 놓았는데 사이트가 열리면 안 되니까)
  if (drag?.moved) {
    justDragged = true
    setTimeout(() => (justDragged = false))
  }
  drag = null
  dragging.value = false
}

let justDragged = false
function open(f: FestivalView) {
  if (!justDragged) openFestivalSite(f)
}

function scrollDays(n: number) {
  scroller.value?.scrollBy({ left: n * DAY_W.value, behavior: 'smooth' })
}
function scrollToday() {
  scroller.value?.scrollTo({ left: Math.max(0, todayIdx.value) * DAY_W.value, behavior: 'smooth' })
}

// ── 보이는 날짜 구간: 이 구간에 열리는 축제로 행을 고른다 ──
const winStart = ref(0)
const winDays = ref(14)
let settleTimer: ReturnType<typeof setTimeout> | undefined
let frame = 0

function measure() {
  const el = scroller.value
  if (!el) return
  winStart.value = Math.floor(el.scrollLeft / DAY_W.value)
  winDays.value = Math.max(1, Math.ceil((el.clientWidth - NAME_W.value) / DAY_W.value))
}
function onScroll() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => {
    const el = scroller.value
    // 끝에서 1주 남으면 다음 4주를 미리 받는다
    if (el && props.canLoadMore && el.scrollLeft + el.clientWidth > el.scrollWidth - 7 * DAY_W.value) emit('loadMore')
  })
  // 끄는 동안 행이 바뀌면 어지러워서, 멈춘 뒤에 바꾼다
  clearTimeout(settleTimer)
  settleTimer = setTimeout(measure, 160)
}
const headerEl = ref<HTMLDivElement>()
const headerH = ref(0)
onMounted(() => {
  measure()
  headerH.value = headerEl.value?.offsetHeight ?? 0
})
watch(wide, () =>
  requestAnimationFrame(() => {
    measure()
    headerH.value = headerEl.value?.offsetHeight ?? 0
  }),
)

const visible = computed(() => ({
  start: addDays(props.start, winStart.value),
  end: addDays(props.start, winStart.value + winDays.value - 1),
}))
const inWindow = computed(() =>
  props.list.filter((f) => f.start && f.end && f.start <= visible.value.end && f.end >= visible.value.start),
)

// ponytail: 처음엔 일부만 그린다. 축제가 수백 건이면 가상 스크롤로.
// 모바일은 화면이 짧아서 5줄만 먼저
const PREVIEW = computed(() => (wide.value ? 10 : 5))
const expanded = ref(false)
watch(() => props.list, () => (expanded.value = false))
const rows = computed(() =>
  (expanded.value ? inWindow.value : inWindow.value.slice(0, PREVIEW.value)).map((f) => ({
    f,
    bar: barSpan(f, props.start, props.end),
  })),
)
const track = computed(() => ({
  gridTemplateColumns: `repeat(${days.value.length}, ${DAY_W.value}px)`,
  width: `${trackW.value}px`,
}))
// 모바일: 막대 줄에만 옅은 바탕과 오늘 표시를 그린다 (축제 이름 줄을 가로지르지 않게)
const mobileTrack = computed(() => {
  const t = todayIdx.value * DAY_W.value + DAY_W.value / 2
  return {
    ...track.value,
    backgroundColor: '#F3F1EC',
    backgroundImage:
      todayIdx.value >= 0
        ? `linear-gradient(90deg, transparent ${t - 1}px, rgb(194 65 12 / 0.5) ${t - 1}px ${t + 1}px, transparent ${t + 1}px)`
        : 'none',
  }
})

const BAR: Record<Status, string> = {
  ongoing: 'bg-accent',
  upcoming: 'bg-upcoming',
  always: 'bg-always',
  ended: 'bg-[#D6D3CB]',
}
function dayColor(dow: number) {
  return dow === 0 ? 'text-accent' : dow === 6 ? 'text-[#1D4ED8]' : 'text-sub'
}
function barClass(status: Status, bar: { openStart: boolean; openEnd: boolean }) {
  return [BAR[status], bar.openStart ? '' : 'rounded-l-full', bar.openEnd ? '' : 'rounded-r-full']
}
</script>

<template>
  <section
    id="overview"
    aria-labelledby="gantt-title"
    class="min-w-0 flex-[999_1_640px] rounded-[18px] border border-line bg-card px-4 pt-[18px] pb-2 md:rounded-[20px] md:px-6 md:pt-6 md:pb-4"
  >
    <div class="mb-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-2 md:mb-4">
      <div class="flex items-baseline gap-2">
        <h2 id="gantt-title" class="text-[17px] font-bold md:text-xl">일정 한눈에</h2>
        <span class="text-xs text-sub md:text-[13px]" aria-live="polite">{{ md(visible.start) }} – {{ md(visible.end) }}</span>
      </div>
      <!-- 한 주씩 넘기기 · 오늘로 -->
      <div class="flex items-center gap-1">
        <button
          type="button"
          aria-label="일정표 이전 주로"
          class="flex size-9 cursor-pointer items-center justify-center rounded-full border border-line transition hover:border-ink active:scale-90 disabled:cursor-default disabled:opacity-40"
          :disabled="winStart === 0"
          @click="scrollDays(-7)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"></path></svg>
        </button>
        <button
          type="button"
          class="min-h-9 cursor-pointer rounded-full border border-line px-3 text-[13px] font-bold transition hover:border-ink active:scale-95"
          @click="scrollToday"
        >
          오늘
        </button>
        <button
          type="button"
          aria-label="일정표 다음 주로"
          class="flex size-9 cursor-pointer items-center justify-center rounded-full border border-line transition hover:border-ink active:scale-90"
          @click="scrollDays(7)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"></path></svg>
        </button>
      </div>
    </div>

    <div
      ref="scroller"
      tabindex="0"
      aria-label="일정표. 좌우로 끌거나 화살표 키로 다음 날짜를 볼 수 있어요"
      class="overflow-x-auto overscroll-x-contain pb-2 [scrollbar-width:thin] focus-visible:outline-2 focus-visible:outline-accent"
      :class="dragging ? 'cursor-grabbing select-none' : 'cursor-grab'"
      @scroll.passive="onScroll"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <div class="relative" :style="{ width: `${NAME_W + trackW}px` }">
        <!-- 배경(PC): 주말 칸, 오늘 세로선. 날짜 머리줄은 빼고 축제 행 영역에만 -->
        <div
          class="pointer-events-none absolute bottom-0 hidden md:block"
          :style="{ left: `${NAME_W}px`, width: `${trackW}px`, top: `${headerH}px` }"
          aria-hidden="true"
        >
          <template v-for="(d, i) in days" :key="d.iso">
            <div
              v-if="d.dow === 0 || d.dow === 6"
              class="absolute inset-y-0 bg-[#F7F5F0]"
              :style="{ left: `${i * DAY_W}px`, width: `${DAY_W}px` }"
            ></div>
          </template>
          <div
            v-if="todayIdx >= 0"
            class="absolute inset-y-0 w-0.5 bg-accent/35"
            :style="{ left: `${todayIdx * DAY_W + DAY_W / 2 - 1}px` }"
          ></div>
        </div>

        <!-- 날짜 머리줄 -->
        <div ref="headerEl" class="relative flex border-b border-line" aria-hidden="true">
          <div
            class="sticky left-0 z-10 hidden flex-none items-end self-stretch bg-card pr-4 pb-2 text-[13px] text-sub md:flex"
            :style="{ width: `${NAME_W}px` }"
          >
            축제
          </div>
          <div class="grid pb-2" :style="track">
            <div v-for="d in days" :key="d.iso" class="flex flex-col items-center gap-0.5">
              <span class="h-4 self-start text-xs font-bold whitespace-nowrap text-ink">{{ d.month }}</span>
              <span class="text-[10px] md:text-[11px]" :class="dayColor(d.dow)">{{ d.isToday ? '오늘' : d.weekday }}</span>
              <span
                class="flex size-6 items-center justify-center rounded-full text-xs font-bold md:size-7 md:text-[13px]"
                :class="d.isToday ? 'bg-ink text-white' : dayColor(d.dow)"
                >{{ d.date }}</span
              >
            </div>
          </div>
        </div>

        <!-- 축제 행 -->
        <ul class="relative">
          <li
            v-for="({ f, bar }, i) in rows"
            :key="f.id"
            class="group border-b border-[#EFEDE7] py-[9px] transition-colors hover:bg-ink/[0.025] md:flex md:items-center md:py-0"
          >
            <div
              class="sticky left-0 z-10 mb-[5px] inline-flex max-w-[calc(100vw-64px)] gap-2 bg-card pr-1 text-[13px] md:mb-0 md:flex md:max-w-none md:flex-none md:flex-col md:justify-center md:gap-0 md:self-stretch md:py-2.5 md:pr-4"
              :style="wide ? { width: `${NAME_W}px` } : undefined"
            >
              <button
                type="button"
                class="cursor-pointer truncate text-left font-bold transition-colors group-hover:text-accent md:text-sm"
                :aria-label="`${f.title} 홈페이지 새 탭에서 열기`"
                @click="open(f)"
              >
                {{ f.title }}
              </button>
              <span class="flex-none truncate text-xs text-sub">
                <span class="md:hidden">{{ f.town }}</span>
                <span class="hidden md:inline">{{ f.place }} · {{ f.range }}</span>
              </span>
            </div>
            <div class="grid h-2.5 rounded-full md:h-[22px] md:rounded-none" :style="wide ? track : mobileTrack">
              <div
                class="relative h-2.5 origin-left animate-bar-grow cursor-pointer transition-[filter] group-hover:brightness-110 md:h-[22px]"
                :class="barClass(f.status, bar)"
                @click="open(f)"
                :style="{ gridColumn: bar.gridColumn, animationDelay: `${Math.min(i, 15) * 35}ms` }"
                :title="`${f.title} ${f.range}`"
              ></div>
            </div>
          </li>
        </ul>

        <!-- 다음 날짜 불러오는 중 -->
        <div
          v-if="loadingMore"
          class="absolute top-1/2 right-2 flex -translate-y-1/2 items-center gap-2 rounded-full bg-card px-3 py-2 text-xs text-sub shadow"
          role="status"
        >
          <span class="size-3.5 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true"></span>
          다음 날짜 불러오는 중…
        </div>
      </div>
    </div>

    <p class="mt-1 flex items-center gap-1.5 text-[11px] text-sub md:text-xs">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M18 8l4 4-4 4M6 8l-4 4 4 4M2 12h20"></path>
      </svg>
      끌어서 넘기면 다음 날짜가 계속 이어져요
    </p>

    <button
      v-if="inWindow.length > PREVIEW"
      type="button"
      class="mt-1 min-h-11 w-full cursor-pointer text-sm font-bold text-sub hover:text-ink"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      {{ expanded ? '접기' : `이 기간 전체 ${inWindow.length}개 보기` }}
    </button>
    <p v-if="inWindow.length === 0" class="py-7 text-center text-sm text-sub md:py-10 md:text-base">
      이 기간에 열리는 축제가 없어요.
    </p>
  </section>
</template>
