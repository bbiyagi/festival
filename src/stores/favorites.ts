import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Festival, Region } from '@/composables/useFestivals'
import { supabase } from '@/utils/supabase'

interface FavoriteRow {
  festival_id: string
  title: string
  start_date: string | null
  end_date: string | null
  is_always: boolean
  place: string | null
  town: string | null
  region: string | null
  image: string | null
  lat: number | null
  lng: number | null
}

const toRow = (f: Festival): FavoriteRow => ({
  festival_id: f.id,
  title: f.title,
  start_date: f.start,
  end_date: f.end,
  is_always: f.isAlways,
  place: f.place,
  town: f.town,
  region: f.region,
  image: f.image,
  lat: f.lat,
  lng: f.lng,
})

const fromRow = (r: FavoriteRow): Festival => ({
  id: r.festival_id,
  title: r.title,
  start: r.start_date,
  end: r.end_date,
  isAlways: r.is_always,
  place: r.place,
  town: r.town,
  region: r.region as Region | null,
  image: r.image,
  // 찜 테이블에 없는 값: 목록에서 다시 받으면 채워진다
  placeDetail: null,
  category: null,
  kind: null,
  thumb: null,
  tel: null,
  lat: r.lat,
  lng: r.lng,
})

/** Supabase 오류를 사용자가 고칠 수 있는 문장으로. */
function explain(e: unknown): string {
  const msg = (e as { message?: string; code?: string })?.message ?? String(e)
  const code = (e as { code?: string })?.code
  if (/anonymous sign-ins are disabled/i.test(msg)) return 'Supabase에서 익명 로그인을 켜야 찜할 수 있어요.'
  if (code === 'PGRST205' || code === '42P01') return '찜 테이블이 아직 없어요. Supabase에서 SQL을 실행해 주세요.'
  return `찜을 저장하지 못했어요. (${msg})`
}

// Supabase에서 SQL을 실행하고 익명 로그인을 켠 뒤 true로 바꾼다 (README > Supabase)
const ENABLED = true
const NOT_READY = '찜한 축제 기능은 아직 준비 중이에요. 조금만 기다려 주세요!'

/**
 * 찜한 축제. 로그인 없이 기기별로 저장한다(Supabase 익명 로그인).
 * 익명 사용자는 처음 찜할 때 만든다 — 구경만 하는 방문자까지 계정을 만들지 않도록.
 */
export const useFavorites = defineStore('favorites', () => {
  const items = ref<Festival[]>([])
  const error = ref<string | null>(null)
  const ids = computed(() => new Set(items.value.map((f) => f.id)))
  let loaded = false

  /** 아직 못 쓰는 기능이면 안내 토스트를 띄운다. */
  function notReady() {
    error.value = NOT_READY
  }

  async function load() {
    if (!ENABLED || !supabase || loaded) return
    const { data: session } = await supabase.auth.getSession()
    if (!session.session) return // 아직 찜한 적 없는 기기
    const { data, error: e } = await supabase.from('favorites').select('*').order('created_at', { ascending: false })
    if (e) {
      error.value = explain(e)
      return
    }
    items.value = (data as FavoriteRow[]).map(fromRow)
    loaded = true
  }

  async function ensureUser() {
    const { data } = await supabase!.auth.getSession()
    if (data.session) return
    const { error: e } = await supabase!.auth.signInAnonymously()
    if (e) throw e
  }

  async function toggle(f: Festival) {
    if (!ENABLED) return notReady()
    if (!supabase) {
      error.value = '찜 기능이 설정되지 않았어요. (VITE_SUPABASE_URL)'
      return
    }
    const saved = ids.value.has(f.id)
    const before = items.value
    // 먼저 화면을 바꾸고, 저장이 실패하면 되돌린다
    items.value = saved ? before.filter((x) => x.id !== f.id) : [f, ...before]
    error.value = null
    try {
      await ensureUser()
      const { error: e } = saved
        ? await supabase.from('favorites').delete().eq('festival_id', f.id)
        : await supabase.from('favorites').upsert(toRow(f))
      if (e) throw e
      loaded = true
    } catch (e) {
      items.value = before
      error.value = explain(e)
    }
  }

  return { enabled: ENABLED, items, error, has: (id: string) => ids.value.has(id), load, toggle, notReady }
})
