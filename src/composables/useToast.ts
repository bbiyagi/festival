import { ref } from 'vue'

export interface Toast {
  text: string
  action?: { label: string; run: () => void }
}

// 화면 아래에 잠깐 뜨는 안내 하나. 새 안내가 오면 이전 것을 바꾼다.
const toast = ref<Toast | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined

export function showToast(text: string, action?: Toast['action']) {
  toast.value = { text, action }
  clearTimeout(timer)
  timer = setTimeout(hideToast, action ? 9000 : 6000) // 버튼이 있으면 누를 시간을 조금 더
}

export function hideToast() {
  clearTimeout(timer)
  toast.value = null
}

export function useToast() {
  return { toast, showToast, hideToast }
}
