import { fetchFestivalLink } from '@/composables/useFestivals'

/**
 * 축제 홈페이지를 새 탭으로 연다. 홈페이지가 없으면 네이버 검색 결과로.
 * 주소를 받아 오는 동안 기다리면 팝업 차단에 걸려서, 누르는 순간 빈 탭부터 연다.
 */
export async function openFestivalSite(f: { id: string; title: string }) {
  const tab = window.open('', '_blank')
  let url = `https://search.naver.com/search.naver?query=${encodeURIComponent(f.title)}`
  try {
    url = (await fetchFestivalLink(f.id)) ?? url
  } catch {
    // 서버 오류면 검색 결과로라도 연다
  }
  if (!tab) {
    window.open(url, '_blank', 'noopener')
    return
  }
  tab.opener = null // 열린 사이트가 이 탭을 조작하지 못하게
  tab.location.href = url
}
