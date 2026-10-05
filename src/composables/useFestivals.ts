import { computed, ref } from 'vue'
import { addDays } from '../utils/festival.ts'

export type Region =
  | 'seoul'
  | 'gyeonggi'
  | 'gangwon'
  | 'chungcheong'
  | 'jeolla'
  | 'gyeongbuk'
  | 'gyeongnam'
  | 'jeju'

export type Kind = 'festival' | 'show' | 'exhibit' | 'event'

export interface Festival {
  id: string
  title: string
  place: string | null // 경남 거창군
  placeDetail: string | null // 강경 금강둔치 일원 (있을 때만)
  town: string | null // 거창 (사진 없을 때 자리표시)
  region: Region | null
  category: string | null // 지역특산물축제, 전시회 …
  kind: Kind | null
  start: string | null // YYYY-MM-DD
  end: string | null
  isAlways: boolean
  image: string | null
  thumb: string | null // 작은 사진
  tel: string | null // 대표 번호 하나
  lat: number | null
  lng: number | null
}

export interface FestivalDetail extends Festival {
  address: string | null
  images: string[]
  overview: string | null
  playtime: string | null
  eventPlace: string | null
  fee: string | null
  price: 'free' | 'partial' | 'paid' | null
  host: string | null
  hostTel: string | null
  organizer: string | null
  organizerTel: string | null
  telName: string | null
  homepage: string | null
  program: string | null
  ageLimit: string | null
  bookingPlace: string | null
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new ApiError(body?.detail ?? `요청 실패 (${res.status})`, res.status)
  }
  return (await res.json()) as T
}

export function fetchFestivals(start: string, end: string): Promise<Festival[]> {
  return getJson(`/api/festivals?${new URLSearchParams({ start, end })}`)
}

export function fetchFestivalDetail(id: string): Promise<FestivalDetail> {
  return getJson(`/api/festivals/${encodeURIComponent(id)}`)
}

export interface FestivalIntro {
  id: string
  playtime: string | null // 10:00~20:00
  price: 'free' | 'partial' | 'paid' | null
}

/** 목록 카드용 운영 시간·무료 여부. 서버가 한 번에 최대 30개까지 받는다. */
export function fetchFestivalIntros(ids: string[]): Promise<FestivalIntro[]> {
  return getJson(`/api/festivals/intro?${new URLSearchParams({ ids: ids.join(',') })}`)
}

/** 축제 홈페이지 (없으면 null). 상세 화면 대신 바로 연다. */
export async function fetchFestivalLink(id: string): Promise<string | null> {
  return (await getJson<{ url: string | null }>(`/api/festivals/${encodeURIComponent(id)}/link`)).url
}

/**
 * start부터 initialDays일을 먼저 받고, loadMore()로 4주씩 이어 받는다 (최대 maxDays일).
 * 일정표를 끌어서 넘길 때 다음 날짜의 축제가 계속 나오도록.
 */
export function useFestivals(start: string, initialDays: number, maxDays: number) {
  const festivals = ref<Festival[]>([])
  const end = ref(addDays(start, initialDays - 1))
  const lastDay = addDays(start, maxDays - 1)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref<ApiError | Error | null>(null)
  const canLoadMore = computed(() => end.value < lastDay)

  async function load() {
    loading.value = true
    error.value = null
    try {
      festivals.value = await fetchFestivals(start, end.value)
    } catch (e) {
      error.value = e as Error
    } finally {
      loading.value = false
    }
  }

  async function loadMore(days = 28) {
    if (loading.value || loadingMore.value || !canLoadMore.value) return
    const from = addDays(end.value, 1)
    const to = [addDays(end.value, days), lastDay].sort()[0]
    loadingMore.value = true
    try {
      const more = await fetchFestivals(from, to)
      // 두 구간에 걸친 축제는 양쪽에서 오므로 id로 한 번만
      const seen = new Set(festivals.value.map((f) => f.id))
      festivals.value = [...festivals.value, ...more.filter((f) => !seen.has(f.id))]
      end.value = to
    } catch {
      // 다음에 끝까지 끌었을 때 다시 시도한다
    } finally {
      loadingMore.value = false
    }
  }

  load()
  return { festivals, end, loading, loadingMore, canLoadMore, error, reload: load, loadMore }
}
