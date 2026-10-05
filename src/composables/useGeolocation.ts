import { ref } from 'vue'
import type { LatLng } from '@/utils/festival'

export type GeoState = 'idle' | 'locating' | 'ok' | 'denied' | 'unavailable'

// 화면 전체가 같은 위치를 쓰도록 모듈에 하나만 둔다. 위치는 브라우저 안에서만 쓰고 서버로 보내지 않는다.
const position = ref<LatLng | null>(null)
const state = ref<GeoState>('idle')

function locate() {
  if (!('geolocation' in navigator)) {
    state.value = 'unavailable'
    return
  }
  state.value = 'locating'
  navigator.geolocation.getCurrentPosition(
    (p) => {
      position.value = { lat: p.coords.latitude, lng: p.coords.longitude }
      state.value = 'ok'
    },
    (e) => (state.value = e.code === e.PERMISSION_DENIED ? 'denied' : 'unavailable'),
    // 축제 거리 정렬에는 대략적인 위치로 충분하다
    { enableHighAccuracy: false, timeout: 10_000, maximumAge: 10 * 60_000 },
  )
}

export function useGeolocation() {
  return { position, state, locate }
}
