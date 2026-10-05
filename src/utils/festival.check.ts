// 화면 규칙 점검: npm run check:web (node가 TypeScript를 바로 실행)
import assert from 'node:assert/strict'
import type { Festival } from '../composables/useFestivals.ts'
import {
  barSpan,
  dayCells,
  distanceKm,
  formatDistance,
  matchesQuery,
  matchesWhen,
  sortFestivals,
  statusOf,
  toView,
  weekendOf,
} from './festival.ts'

const TODAY = '2026-10-07' // 수요일
const f = (over: Partial<Festival>): Festival => ({
  id: 'x', title: 'x', place: null, placeDetail: null, town: null, region: null, category: null, kind: null,
  start: null, end: null, isAlways: false, image: null, thumb: null, tel: null, lat: null, lng: null, ...over,
})

// 상태와 D-day
assert.deepEqual(statusOf(f({ start: '2026-10-01', end: '2026-10-07' }), TODAY), { status: 'ongoing', statusLabel: '진행중', dday: '오늘 마감', urgent: true })
assert.equal(statusOf(f({ start: '2026-10-01', end: '2026-10-20' }), TODAY).dday, '마감 D-13')
assert.equal(statusOf(f({ start: '2026-10-01', end: '2026-10-20' }), TODAY).urgent, false)
assert.equal(statusOf(f({ start: '2026-10-10', end: '2026-10-12' }), TODAY).dday, '오픈 D-3')
assert.equal(statusOf(f({ start: '2026-10-05', end: '2026-10-06' }), TODAY).status, 'ended')
assert.equal(statusOf(f({ start: '2026-01-01', end: '2026-12-31', isAlways: true }), TODAY).status, 'always')

// 거리: 서울시청 ↔ 부산시청 약 325km
const SEOUL = { lat: 37.5663, lng: 126.9779 }
assert.ok(Math.abs(distanceKm(SEOUL, { lat: 35.1798, lng: 129.075 }) - 325) < 5)
assert.equal(formatDistance(0.84), '800m')
assert.equal(formatDistance(3.24), '3.2km')
assert.equal(formatDistance(42.6), '43km')

// 정렬: 끝난 축제 다음, 상시 맨 뒤 (어느 정렬이든)
const list = [
  f({ id: 'always', start: '2026-01-01', end: '2026-12-31', isAlways: true, lat: 37.57, lng: 126.98 }),
  f({ id: 'late-far', start: '2026-10-01', end: '2026-10-30', lat: 35.18, lng: 129.07 }),
  f({ id: 'ended', start: '2026-10-05', end: '2026-10-06' }),
  f({ id: 'soon-near', start: '2026-10-09', end: '2026-10-09', lat: 37.6, lng: 127.0 }),
  f({ id: 'no-coord', start: '2026-10-08', end: '2026-10-08' }),
].map((x) => toView(x, TODAY, SEOUL))
assert.deepEqual(sortFestivals(list, 'deadline').map((x) => x.id), ['no-coord', 'soon-near', 'late-far', 'ended', 'always'])
assert.deepEqual(sortFestivals(list, 'start').map((x) => x.id), ['late-far', 'no-coord', 'soon-near', 'ended', 'always'])
assert.deepEqual(sortFestivals(list, 'near').map((x) => x.id), ['soon-near', 'late-far', 'no-coord', 'ended', 'always'])
assert.equal(toView(list[0], TODAY, null).distanceKm, null) // 위치 모르면 거리 없음

// 주말: 수요일 → 이번 토·일, 일요일 → 어제 토요일부터
assert.deepEqual(weekendOf(TODAY), { start: '2026-10-10', end: '2026-10-11' })
assert.deepEqual(weekendOf(TODAY, 1), { start: '2026-10-17', end: '2026-10-18' })
assert.deepEqual(weekendOf('2026-10-11'), { start: '2026-10-10', end: '2026-10-11' })
const v = (over: Partial<Festival>) => toView(f(over), TODAY)
assert.ok(matchesWhen(v({ start: '2026-10-11', end: '2026-10-20' }), 'weekend', TODAY))
assert.ok(!matchesWhen(v({ start: '2026-10-12', end: '2026-10-16' }), 'weekend', TODAY))
assert.ok(matchesWhen(v({ start: '2026-10-12', end: '2026-10-17' }), 'nextWeekend', TODAY))
assert.ok(!matchesWhen(v({ start: '2026-10-09', end: '2026-10-12' }), 'now', TODAY)) // 아직 시작 전
assert.ok(matchesWhen(v({ isAlways: true, start: '2026-01-01', end: '2026-12-31' }), 'now', TODAY))

// 일정표 막대: 기간 밖으로 이어지는 쪽은 열림
assert.deepEqual(barSpan(f({ start: '2026-09-18', end: '2026-10-08' }), '2026-10-05', '2026-10-11'), { gridColumn: '1 / 5', openStart: true, openEnd: false })
assert.deepEqual(barSpan(f({ start: '2026-10-11', end: '2026-10-20' }), '2026-10-05', '2026-10-11'), { gridColumn: '7 / 8', openStart: false, openEnd: true })

// 날짜 칸: 모든 날짜·요일, 첫 칸과 1일에 'n월'
const days = dayCells('2026-10-07', '2026-11-17', TODAY)
assert.equal(days.length, 42)
assert.deepEqual([days[0].month, days[0].date, days[0].weekday, days[0].isToday], ['10월', 7, '수', true])
assert.deepEqual(days.slice(1, 4).map((d) => d.month), ['', '', ''])
const nov1 = days.find((d) => d.iso === '2026-11-01')!
assert.deepEqual([nov1.month, nov1.date, nov1.weekday], ['11월', 1, '일'])

// 검색
const seoul = f({ title: '문화가 흐르는 서울광장', place: '서울 중구', category: '기타공연', town: '중구' })
assert.ok(matchesQuery(seoul, ''))
assert.ok(matchesQuery(seoul, '서울 광장')) // 띄어쓰기 무시
assert.ok(matchesQuery(seoul, '중구 공연')) // 장소 + 분류
assert.ok(!matchesQuery(seoul, '서울 불꽃'))
assert.ok(matchesQuery(f({ title: 'Colorful Garden' }), 'colorful'))

console.log('festival.check: ok')
