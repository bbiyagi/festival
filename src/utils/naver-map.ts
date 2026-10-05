// 네이버 지도 JS v3. 지도 탭을 처음 열 때만 스크립트를 불러온다.
// 신규 콘솔 키는 ncpKeyId 파라미터로 인증한다 (PhotoShare에서 확인).

import { ref } from 'vue'

// ponytail: 쓰는 API가 몇 개뿐이라 타입은 any. 많이 쓰게 되면 @types/navermaps로.
export type NaverMaps = any

declare global {
  interface Window {
    naver?: { maps: NaverMaps }
    navermap_authFailure?: () => void
  }
}

export type MapLoadError = 'NO_KEY' | 'AUTH' | 'NETWORK'

let loading: Promise<NaverMaps> | null = null
/** 스크립트를 다 불러온 뒤에 인증 실패가 올 수도 있어서 반응형으로도 알린다. */
export const authFailed = ref(false)

export function loadNaverMaps(): Promise<NaverMaps> {
  if (window.naver?.maps) return Promise.resolve(window.naver.maps)
  if (loading) return loading
  const clientId = import.meta.env.VITE_NAVER_MAP_CLIENT_ID
  if (!clientId) return Promise.reject<NaverMaps>('NO_KEY' satisfies MapLoadError)

  loading = new Promise<NaverMaps>((resolve, reject) => {
    // 키가 틀렸거나 서비스 URL이 등록되지 않으면 네이버가 이 함수를 부른다
    window.navermap_authFailure = () => {
      authFailed.value = true
      reject('AUTH' satisfies MapLoadError)
    }
    const script = document.createElement('script')
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(clientId)}`
    script.async = true
    script.onload = () => (window.naver?.maps ? resolve(window.naver.maps) : reject('NETWORK'))
    script.onerror = () => {
      loading = null // 네트워크 오류는 다시 시도할 수 있게
      reject('NETWORK' satisfies MapLoadError)
    }
    document.head.appendChild(script)
  })
  return loading
}
