-- Stellinerary per-user trips. Run once in the Supabase SQL editor.
-- Authenticated users' plans are stored here; anonymous plans stay in the
-- backend's local SQLite store.

create table if not exists public.trips (
  user_id uuid not null references auth.users (id) on delete cascade,
  plan_id text primary key,
  observation_end date not null,
  updated_at timestamptz not null default now(),
  payload jsonb not null
);

create index if not exists trips_user_updated_idx
  on public.trips (user_id, updated_at desc);

alter table public.trips enable row level security;

drop policy if exists "Users manage own trips" on public.trips;
create policy "Users manage own trips"
  on public.trips for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
