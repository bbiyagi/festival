import { reactive } from 'vue'
import { fetchFestivalIntros, type FestivalIntro } from '@/composables/useFestivals'

const CHUNK = 30 // 서버 한도

// 화면 전체가 같은 값을 쓰도록 모듈에 하나만 둔다. null = 받았지만 정보 없음.
const intros = reactive(new Map<string, FestivalIntro | null>())
const pending = new Set<string>()

/** 아직 모르는 축제의 운영 시간·무료 여부를 받아 온다. 화면에 보이는 카드만 넘긴다. */
async function want(ids: string[]) {
  const missing = ids.filter((id) => !intros.has(id) && !pending.has(id))
  for (let i = 0; i < missing.length; i += CHUNK) {
    const chunk = missing.slice(i, i + CHUNK)
    chunk.forEach((id) => pending.add(id))
    try {
      const got = await fetchFestivalIntros(chunk)
      const byId = new Map(got.map((x) => [x.id, x]))
      chunk.forEach((id) => intros.set(id, byId.get(id) ?? null))
    } catch {
      // 실패하면 표시만 안 하고, 다음에 다시 보일 때 재시도한다
    } finally {
      chunk.forEach((id) => pending.delete(id))
    }
  }
}

export function useIntros() {
  return { intros, want }
}
