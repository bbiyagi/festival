// 오늘 날짜에 따라 바뀌는 화면 규칙 (시안 FESTA PICK의 계산을 옮김).
// 날짜·권역·상시 같은 데이터 규칙은 서버(api/festival_rules.py)가 정하고, 여기서는 표시만 정한다.
// 다른 파일을 import하지 않는다: festival.check.ts를 node로 바로 돌리기 위해.
import type { Festival, Kind, Region } from '../composables/useFestivals.ts'

export interface RegionMeta {
  id: Region
  label: string
  tint: string
  area: string // 지역 타일 grid-area
}

/** 칩·타일 순서. tint는 사진 없을 때 자리표시 색 (노션 시안 기준값). */
export const REGIONS: readonly RegionMeta[] = [
  { id: 'seoul', label: '서울', tint: '#DCE4F2', area: 'se' },
  { id: 'gyeonggi', label: '경기·인천', tint: '#DFEBD8', area: 'gi' },
  { id: 'gangwon', label: '강원', tint: '#D6E9E7', area: 'gw' },
  { id: 'chungcheong', label: '충청', tint: '#EFE5CF', area: 'cc' },
  { id: 'jeolla', label: '전라', tint: '#F3DCCF', area: 'jl' },
  { id: 'gyeongbuk', label: '경북·대구', tint: '#E4DCEF', area: 'gb' },
  { id: 'gyeongnam', label: '경남·부산', tint: '#F1D7DE', area: 'gn' },
  { id: 'jeju', label: '제주', tint: '#D9E9F4', area: 'jj' },
]
export const REGION_BY_ID = Object.fromEntries(REGIONS.map((r) => [r.id, r])) as Record<
  Region,
  RegionMeta
>
export const FALLBACK_TINT = '#ECEAE4'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']
const DAY = 86_400_000

const utc = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d)
}
/** a - b (일) */
export const diffDays = (a: string, b: string) => Math.round((utc(a) - utc(b)) / DAY)
export const addDays = (iso: string, n: number) => new Date(utc(iso) + n * DAY).toISOString().slice(0, 10)
export const weekday = (iso: string) => WEEKDAYS[new Date(utc(iso)).getUTCDay()]
/** 10.5 */
export const md = (iso: string) => {
  const d = new Date(utc(iso))
  return `${d.getUTCMonth() + 1}.${d.getUTCDate()}`
}

export type Status = 'ongoing' | 'upcoming' | 'always' | 'ended'

export interface LatLng {
  lat: number
  lng: number
}

export interface FestivalView extends Festival {
  status: Status
  statusLabel: string
  dday: string
  urgent: boolean // 마감 7일 이내 → 강조색
  range: string // 10.8–10.11
  rangeLong: string // 10.8 (목) – 10.11 (일)
  tint: string
  distanceKm: number | null // 내 위치를 알 때만
}

export function statusOf(f: Festival, today: string): Pick<FestivalView, 'status' | 'statusLabel' | 'dday' | 'urgent'> {
  if (f.isAlways) return { status: 'always', statusLabel: '상시', dday: '연중 운영', urgent: false }
  if (f.start && f.start > today) {
    return { status: 'upcoming', statusLabel: '예정', dday: `오픈 D-${diffDays(f.start, today)}`, urgent: false }
  }
  if (f.end && f.end < today) return { status: 'ended', statusLabel: '종료', dday: '종료', urgent: false }
  const left = f.end ? diffDays(f.end, today) : null
  return {
    status: 'ongoing',
    statusLabel: '진행중',
    dday: left === null ? '진행중' : left === 0 ? '오늘 마감' : `마감 D-${left}`,
    urgent: left !== null && left <= 7,
  }
}

function ranges(f: Festival): Pick<FestivalView, 'range' | 'rangeLong'> {
  if (f.isAlways) return { range: '연중 상시', rangeLong: '연중 상시 운영' }
  if (!f.start || !f.end) return { range: '일정 미정', rangeLong: '일정 미정' }
  if (f.start === f.end) return { range: md(f.start), rangeLong: `${md(f.start)} (${weekday(f.start)})` }
  return {
    range: `${md(f.start)}–${md(f.end)}`,
    rangeLong: `${md(f.start)} (${weekday(f.start)}) – ${md(f.end)} (${weekday(f.end)})`,
  }
}

/** 두 좌표 사이 직선거리(km, 하버사인). */
export function distanceKm(a: LatLng, b: LatLng): number {
  const rad = Math.PI / 180
  const dLat = (b.lat - a.lat) * rad
  const dLng = (b.lng - a.lng) * rad
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}

/** 850m · 3.2km · 12km */
export function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 10) * 100}m`
  return km < 10 ? `${km.toFixed(1)}km` : `${Math.round(km)}km`
}

export function toView(f: Festival, today: string, here: LatLng | null = null): FestivalView {
  return {
    ...f,
    ...statusOf(f, today),
    ...ranges(f),
    tint: f.region ? REGION_BY_ID[f.region].tint : FALLBACK_TINT,
    distanceKm: here && f.lat !== null && f.lng !== null ? distanceKm(here, { lat: f.lat, lng: f.lng }) : null,
  }
}

export type SortKey = 'near' | 'deadline' | 'start'
export const SORTS: { id: SortKey; label: string }[] = [
  { id: 'near', label: '가까운 순' },
  { id: 'deadline', label: '마감 임박순' },
  { id: 'start', label: '시작일순' },
]

// 진행중·예정 → 이미 끝난 축제 → 상시 (상시는 어느 정렬이든 맨 뒤)
const GROUP: Record<Status, number> = { ongoing: 0, upcoming: 0, ended: 1, always: 2 }

export function sortFestivals(list: FestivalView[], sort: SortKey): FestivalView[] {
  const key = (f: FestivalView) =>
    sort === 'start' ? `${f.start ?? '9999'}${f.end ?? ''}` : `${f.end ?? '9999'}${f.start ?? ''}`
  // 가까운 순: 거리를 모르는 축제(좌표 없음)는 뒤로, 같은 거리면 마감 임박순
  const near = (a: FestivalView, b: FestivalView) =>
    sort === 'near' ? (a.distanceKm ?? Infinity) - (b.distanceKm ?? Infinity) : 0
  return [...list].sort(
    (a, b) =>
      GROUP[a.status] - GROUP[b.status] || near(a, b) || key(a).localeCompare(key(b)) || a.title.localeCompare(b.title),
  )
}

export const KINDS: { id: Kind | 'all'; label: string }[] = [
  { id: 'all', label: '전체' },
  { id: 'festival', label: '축제' },
  { id: 'show', label: '공연' },
  { id: 'exhibit', label: '전시·박람회' },
  { id: 'event', label: '행사' },
]

/** 검색: 띄어쓰기로 나눈 낱말이 모두 이름·장소·분류에 들어 있으면. 띄어쓰기·대소문자 무시 ('서울 광장' = '서울광장'). */
export function matchesQuery(f: Festival, q: string): boolean {
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean)
  if (terms.length === 0) return true
  const hay = [f.title, f.place, f.placeDetail, f.town, f.category].join(' ').toLowerCase().replace(/\s+/g, '')
  return terms.every((t) => hay.includes(t))
}

export type When = 'all' | 'now' | 'weekend' | 'nextWeekend'
export const WHENS: { id: When; label: string }[] = [
  { id: 'all', label: '전체' },
  { id: 'now', label: '진행중' },
  { id: 'weekend', label: '이번 주말' },
  { id: 'nextWeekend', label: '다음 주말' },
]

/** 이번 주말(토~일). 오늘이 일요일이면 어제 토요일부터. weeks만큼 뒤 주말. */
export function weekendOf(today: string, weeks = 0): { start: string; end: string } {
  const dow = new Date(utc(today)).getUTCDay()
  const sat = addDays(today, (dow === 0 ? -1 : 6 - dow) + weeks * 7)
  return { start: sat, end: addDays(sat, 1) }
}

export function matchesWhen(f: FestivalView, when: When, today: string): boolean {
  if (when === 'all') return true
  if (when === 'now') return f.status === 'ongoing' || f.status === 'always'
  const w = weekendOf(today, when === 'weekend' ? 0 : 1)
  return f.isAlways || (!!f.start && !!f.end && f.start <= w.end && f.end >= w.start)
}

/** 일정표 막대: 기간 안으로 자른 grid-column과, 기간 밖으로 이어지는 쪽(끝을 각지게). */
export function barSpan(f: Festival, start: string, end: string) {
  const s = !f.start || f.start < start ? start : f.start
  const e = !f.end || f.end > end ? end : f.end
  return {
    gridColumn: `${diffDays(s, start) + 1} / ${diffDays(e, start) + 2}`,
    openStart: !f.start || f.start < start,
    openEnd: !f.end || f.end > end,
  }
}

export interface DayCell {
  iso: string
  isToday: boolean
  dow: number
  weekday: string
  date: number
  month: string // 첫 칸과 1일에만 'n월'
}

export function dayCells(start: string, end: string, today: string): DayCell[] {
  const cells: DayCell[] = []
  for (let i = 0; i <= diffDays(end, start); i++) {
    const iso = addDays(start, i)
    const dow = new Date(utc(iso)).getUTCDay()
    const date = Number(iso.slice(8))
    cells.push({
      iso,
      isToday: iso === today,
      dow,
      weekday: WEEKDAYS[dow],
      date,
      month: i === 0 || date === 1 ? `${Number(iso.slice(5, 7))}월` : '',
    })
  }
  return cells
}
