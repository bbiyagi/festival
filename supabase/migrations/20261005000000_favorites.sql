-- 찜한 축제. Supabase 대시보드 > SQL Editor에서 한 번 실행한다.
-- 로그인 없이 기기별로 쓰도록 익명 로그인(Authentication > Sign In / Providers > Allow anonymous sign-ins)을 켠다.
-- 익명 사용자도 role은 authenticated라 아래 정책으로 자기 찜만 읽고 쓴다.

create table if not exists public.favorites (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  festival_id text not null,
  -- 찜 목록·알림·캘린더를 TourAPI 호출 없이 그리기 위한 축제 정보 사본
  title text not null,
  start_date date,
  end_date date,
  is_always boolean not null default false,
  place text,
  town text,
  region text,
  image text,
  lat double precision,
  lng double precision,
  created_at timestamptz not null default now(),
  primary key (user_id, festival_id)
);

alter table public.favorites enable row level security;

drop policy if exists "favorites: own rows" on public.favorites;
create policy "favorites: own rows" on public.favorites
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- 알림 예약 작업이 "곧 시작하는 찜"을 찾을 때 쓰는 인덱스
create index if not exists favorites_start_date_idx on public.favorites (start_date);
