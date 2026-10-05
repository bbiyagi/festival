import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

/** 키가 없으면 null. 찜 기능만 꺼지고 나머지 화면은 그대로 동작한다. */
export const supabase = url && key ? createClient(url, key) : null
