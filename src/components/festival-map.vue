<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { fetchFestivalDetail, type FestivalDetail } from '@/composables/useFestivals'
import { openFestivalSite } from '@/utils/open-site'
import { useFavorites } from '@/stores/favorites'
import { formatDistance, type FestivalView, type LatLng, type Status } from '@/utils/festival'
import { authFailed, loadNaverMaps, type MapLoadError, type NaverMaps } from '@/utils/naver-map'

const props = defineProps<{ list: FestivalView[]; here: LatLng | null }>()
const favorites = useFavorites()
const selectedId = defineModel<string | null>('selected', { required: true })

const KOREA = { lat: 36.3, lng: 127.8, zoom: 7 }
const COLOR: Record<Status, string> = {
  ongoing: '#C2410C',
  upcoming: '#16181D',
  always: '#A8A49A',
  ended: '#D6D3CB',
}
const BADGE: Record<Status, string> = {
  ongoing: 'bg-accent text-white',
  upcoming: 'bg-upcoming text-white',
  always: 'bg-sub text-white',
  ended: 'bg-[#D6D3CB] text-ink',
}

const mapEl = ref<HTMLDivElement>()
const listEl = ref<HTMLUListElement>()
const state = ref<'loading' | 'ready' | MapLoadError>('loading')
let maps: NaverMaps
let map: NaverMaps
const markers = new Map<string, { marker: NaverMaps; el: HTMLDivElement }>()
let hereMarker: NaverMaps = null

const located = computed(() => props.list.filter((f) => f.lat !== null && f.lng !== null))
const missing = computed(() => props.list.length - located.value.length)
const selected = computed(() => props.list.find((f) => f.id === selectedId.value) ?? null)

function renderMarkers() {
  markers.forEach(({ marker }) => marker.setMap(null))
  markers.clear()
  for (const f of located.value) {
    const el = document.createElement('div')
    el.className = 'fm-marker'
    el.style.background = COLOR[f.status]
    el.title = f.title
    const marker = new maps.Marker({
      map,
      position: new maps.LatLng(f.lat, f.lng),
      icon: { content: el, anchor: new maps.Point(12, 12) },
      zIndex: f.status === 'ongoing' ? 2 : 1,
    })
    maps.Event.addListener(marker, 'click', () => (selectedId.value = f.id))
    markers.set(f.id, { marker, el })
  }
  highlight(selectedId.value, null)
}

function renderHere() {
  hereMarker?.setMap(null)
  hereMarker = null
  if (!props.here) return
  const el = document.createElement('div')
  el.className = 'fm-here'
  el.title = '내 위치'
  hereMarker = new maps.Marker({
    map,
    position: new maps.LatLng(props.here.lat, props.here.lng),
    icon: { content: el, anchor: new maps.Point(11, 11) },
    zIndex: 200,
    clickable: false,
  })
}

function goHere() {
  if (!props.here) return
  map.morph(new maps.LatLng(props.here.lat, props.here.lng), 11, { duration: 500 })
}

function fitAll() {
  const points = located.value.map((f) => new maps.LatLng(f.lat, f.lng))
  if (points.length === 0) {
    map.setCenter(new maps.LatLng(KOREA.lat, KOREA.lng))
    map.setZoom(KOREA.zoom)
  } else if (points.length === 1) {
    map.setCenter(points[0])
    map.setZoom(12)
  } else {
    const bounds = new maps.LatLngBounds(points[0], points[0])
    points.forEach((p) => bounds.extend(p))
    map.fitBounds(bounds, { top: 48, right: 48, bottom: 48, left: 48 })
  }
}

function highlight(id: string | null, prev: string | null) {
  if (prev) markers.get(prev)?.el.classList.remove('is-selected')
  const hit = id ? markers.get(id) : null
  if (!hit) return
  hit.el.classList.add('is-selected')
  hit.marker.setZIndex(100)
  map.panTo(hit.marker.getPosition(), { duration: 400 })
}

async function init() {
  state.value = 'loading'
  try {
    maps = await loadNaverMaps()
  } catch (e) {
    state.value = e as MapLoadError
    return
  }
  if (!mapEl.value) return
  map = new maps.Map(mapEl.value, {
    center: new maps.LatLng(KOREA.lat, KOREA.lng),
    zoom: KOREA.zoom,
    zoomControl: true,
    zoomControlOptions: { position: maps.Position.RIGHT_CENTER }, // 오른쪽 위는 "내 위치" 버튼 자리
    mapDataControl: false,
    scaleControl: false,
  })
  maps.Event.addListener(map, 'click', () => (selectedId.value = null))
  state.value = authFailed.value ? 'AUTH' : 'ready'
  renderMarkers()
  renderHere()
  if (!selectedId.value) fitAll()
}

onMounted(init)
onBeforeUnmount(() => {
  markers.forEach(({ marker }) => marker.setMap(null))
  hereMarker?.setMap(null)
  map?.destroy?.()
})
watch(authFailed, (v) => v && (state.value = 'AUTH'))
watch(
  () => props.here,
  () => state.value === 'ready' && renderHere(),
)
watch(located, () => {
  if (state.value !== 'ready') return
  renderMarkers()
  fitAll()
})
watch(selectedId, async (id, prev) => {
  if (state.value === 'ready') highlight(id, prev ?? null)
  await nextTick()
  listEl.value?.querySelector('[aria-current="true"]')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
})

// 마커를 누르면 상세를 불러와 설명·요금·운영 시간·장소를 보여 준다. 서버가 1시간 캐시.
type CardInfo = Pick<FestivalDetail, 'overview' | 'fee' | 'price' | 'playtime' | 'eventPlace'>
const infos = new Map<string, CardInfo | null>()
const info = ref<CardInfo | null | undefined>() // undefined = 불러오는 중
watch(
  selectedId,
  async (id) => {
    if (!id) return
    if (infos.has(id)) {
      info.value = infos.get(id)
      return
    }
    info.value = undefined
    const d = await fetchFestivalDetail(id).catch(() => null)
    const got = d && { overview: d.overview, fee: d.fee, price: d.price, playtime: d.playtime, eventPlace: d.eventPlace }
    infos.set(id, got)
    if (selectedId.value === id) info.value = got
  },
  { immediate: true },
)

const PRICE: Record<'free' | 'partial' | 'paid', { label: string; cls: string }> = {
  free: { label: '무료', cls: 'bg-[#E3F1E7] text-[#1E6B3A]' },
  partial: { label: '일부 유료', cls: 'bg-[#FFF1DC] text-[#8A4B00]' },
  paid: { label: '유료', cls: 'bg-[#ECEAE4] text-ink' },
}

const ERROR_TEXT: Record<MapLoadError, string> = {
  NO_KEY: '네이버 지도 키(VITE_NAVER_MAP_CLIENT_ID)가 설정되지 않았어요.',
  AUTH: '네이버 지도 인증에 실패했어요. 키와 서비스 URL 등록을 확인해 주세요.',
  NETWORK: '지도를 불러오지 못했어요.',
}
</script>

<template>
  <section aria-label="지도로 보기" class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
    <div
      class="relative h-[62vh] min-h-[420px] overflow-hidden rounded-[18px] border border-line bg-[#E9E7E1] md:h-[640px] md:rounded-[20px]"
    >
      <div ref="mapEl" class="size-full" role="application" aria-label="축제 위치 지도"></div>

      <!-- 범례 + 위치 없는 축제 -->
      <div
        class="pointer-events-none absolute top-3 left-3 flex flex-col gap-1.5 rounded-xl bg-card/95 px-3 py-2 text-xs text-sub shadow-sm"
      >
        <div class="flex gap-3">
          <span class="inline-flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-accent"></span>진행중</span>
          <span class="inline-flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-upcoming"></span>예정</span>
          <span class="inline-flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-always"></span>상시</span>
        </div>
        <span v-if="missing > 0">위치 정보 없음 {{ missing }}곳</span>
      </div>

      <button
        v-if="here && state === 'ready'"
        type="button"
        class="absolute top-[52px] right-2.5 flex min-h-10 cursor-pointer items-center gap-1.5 rounded-full bg-card px-3.5 text-sm font-bold text-[#1D4ED8] shadow-md transition hover:shadow-lg active:scale-95"
        @click="goHere"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4"></circle>
          <path d="M12 2v3M12 19v3M2 12h3M19 12h3"></path>
        </svg>
        내 위치
      </button>

      <!-- 불러오는 중 / 오류 / 표시할 축제 없음 -->
      <div
        v-if="state !== 'ready'"
        class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-bg/90 p-6 text-center"
        role="status"
      >
        <template v-if="state === 'loading'">
          <span class="size-6 animate-spin rounded-full border-2 border-line border-t-accent" aria-hidden="true"></span>
          <p class="text-sub">지도를 불러오는 중…</p>
        </template>
        <template v-else>
          <p class="font-bold">{{ ERROR_TEXT[state] }}</p>
          <button
            v-if="state === 'NETWORK'"
            type="button"
            class="min-h-11 cursor-pointer rounded-full bg-ink px-6 font-bold text-white transition active:scale-95"
            @click="init"
          >
            다시 시도
          </button>
        </template>
      </div>
      <p
        v-else-if="located.length === 0"
        class="absolute inset-x-0 top-1/2 mx-auto w-fit -translate-y-1/2 rounded-full bg-card px-5 py-3 text-sm text-sub shadow"
      >
        이 조건에 지도에 표시할 축제가 없어요.
      </p>

      <!-- 선택한 축제 카드 -->
      <article
        v-if="selected"
        :key="selected.id"
        class="absolute inset-x-3 bottom-3 flex animate-pop-in gap-3 rounded-2xl border border-line bg-card p-3 shadow-lg md:right-auto md:w-[380px]"
        aria-live="polite"
      >
        <div
          class="relative flex size-[88px] flex-none items-end overflow-hidden rounded-xl p-2"
          :style="{ background: selected.tint }"
        >
          <img v-if="selected.image" :src="selected.thumb ?? selected.image" alt="" class="absolute inset-0 size-full object-cover" />
          <span v-else class="font-display text-lg opacity-85" aria-hidden="true">{{ selected.town }}</span>
        </div>
        <div class="flex min-w-0 flex-1 flex-col gap-1 pr-9">
          <div class="flex flex-wrap items-center gap-1.5 text-[11px] font-bold">
            <span class="rounded-full px-2 py-0.5" :class="BADGE[selected.status]">{{ selected.statusLabel }}</span>
            <span v-if="info?.price" class="rounded-full px-2 py-0.5" :class="PRICE[info.price].cls">{{ PRICE[info.price].label }}</span>
            <span :class="selected.urgent ? 'text-accent' : 'text-ink'">{{ selected.dday }}</span>
            <span v-if="selected.category" class="font-medium text-sub">· {{ selected.category }}</span>
          </div>
          <h3 class="text-[15px] leading-snug font-bold">{{ selected.title }}</h3>
          <p class="text-xs text-sub">
            {{ selected.rangeLong }} · {{ selected.place
            }}<template v-if="selected.distanceKm !== null"> · {{ formatDistance(selected.distanceKm) }}</template>
          </p>
          <!-- 운영 시간 · 행사 장소 (상세에서) -->
          <ul v-if="info?.playtime || info?.eventPlace || selected.placeDetail" class="flex flex-col gap-0.5 text-xs text-[#3F434B]">
            <li v-if="info?.playtime" class="flex gap-1.5">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true" class="mt-0.5 flex-none text-sub">
                <circle cx="12" cy="12" r="9"></circle>
                <path d="M12 7v5l3 2"></path>
              </svg>
              <span class="sr-only">운영 시간</span><span class="line-clamp-1">{{ info.playtime }}</span>
            </li>
            <li v-if="info?.eventPlace || selected.placeDetail" class="flex gap-1.5">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="mt-0.5 flex-none text-sub">
                <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              <span class="sr-only">장소</span><span class="line-clamp-1">{{ info?.eventPlace ?? selected.placeDetail }}</span>
            </li>
          </ul>
          <p v-if="info === undefined" class="text-xs text-sub">정보 불러오는 중…</p>
          <p v-else-if="info?.overview" class="line-clamp-2 text-xs leading-relaxed text-[#3F434B]">{{ info.overview }}</p>
          <div class="mt-1 flex flex-wrap gap-1.5">
            <button
              type="button"
              class="inline-flex min-h-9 cursor-pointer items-center gap-1 rounded-full bg-ink px-3.5 text-xs font-bold text-white transition hover:bg-accent active:scale-95"
              @click="openFestivalSite(selected)"
            >
              홈페이지 보기
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M7 17 17 7M8 7h9v9"></path>
              </svg>
              <span class="sr-only">(새 탭)</span>
            </button>
            <a
              v-if="selected.tel"
              :href="`tel:${selected.tel}`"
              class="inline-flex min-h-9 items-center gap-1 rounded-full border border-line px-3.5 text-xs font-bold text-ink no-underline transition hover:border-ink active:scale-95"
              :aria-label="`문의 전화 ${selected.tel}`"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"></path>
              </svg>
              {{ selected.tel }}
            </a>
          </div>
        </div>
        <button
          type="button"
          :aria-label="favorites.has(selected.id) ? '찜 해제' : '찜하기'"
          :aria-pressed="favorites.has(selected.id)"
          class="absolute right-1.5 bottom-1.5 flex size-10 cursor-pointer items-center justify-center rounded-full text-accent transition hover:scale-110 active:scale-90"
          @click="favorites.toggle(selected)"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" :fill="favorites.has(selected.id) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"></path>
          </svg>
        </button>
        <button
          type="button"
          aria-label="닫기"
          class="absolute top-1.5 right-1.5 flex size-9 cursor-pointer items-center justify-center rounded-full text-sub transition hover:bg-bg hover:text-ink"
          @click="selectedId = null"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
            <path d="M18 6 6 18M6 6l12 12"></path>
          </svg>
        </button>
      </article>
    </div>

    <!-- PC: 지도 옆 목록. 누르면 지도에서 그 축제로 이동 -->
    <ul
      ref="listEl"
      class="hidden h-[640px] flex-col gap-1 overflow-y-auto rounded-[20px] border border-line bg-card p-2 lg:flex"
      aria-label="지도에 표시된 축제"
    >
      <li v-for="f in list" :key="f.id">
        <button
          type="button"
          :aria-current="f.id === selectedId"
          :disabled="f.lat === null"
          class="flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-left transition hover:bg-bg disabled:cursor-default disabled:opacity-50 aria-[current=true]:bg-ink aria-[current=true]:text-white"
          @click="selectedId = f.id"
        >
          <span class="size-2.5 flex-none rounded-full ring-2 ring-white" :style="{ background: COLOR[f.status] }"></span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-bold">{{ f.title }}</span>
            <span class="block truncate text-xs opacity-70">{{ f.place }} · {{ f.range }}</span>
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>
