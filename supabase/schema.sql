-- ============================================================================
--  RiskLens — database schema (Supabase / PostgreSQL)
-- ----------------------------------------------------------------------------
--  Run this ONCE in Supabase: Dashboard → SQL Editor → New query → paste → Run.
--  Creates the app's tables, auto-creates a profile when someone signs up,
--  and locks every table so each user can only ever see their OWN rows.
--
--  What gets created:
--    profiles        -> one row per user (name, plan: free/paid, settings)
--    holdings        -> a user's PORTFOLIO: what they bought, how much, price (for ROI)
--    risk_answers    -> each wizard run: their answers + the Buy/Maybe/Avoid result
--    watchlist_items -> securities a user chooses to follow
--  (The "users" table itself is built into Supabase auth — we just link to it.)
-- ============================================================================


-- 1) PROFILES ---------------------------------------------------------------
create table if not exists public.profiles (
  id          uuid        primary key references auth.users (id) on delete cascade,
  email       text,
  full_name   text,
  plan        text        not null default 'free',          -- 'free' | 'paid' (subscriptions later)
  settings    jsonb       not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
comment on table public.profiles is 'One row per user. Linked to auth.users. plan drives free vs paid later.';


-- 2) HOLDINGS (portfolio) ---------------------------------------------------
create table if not exists public.holdings (
  id              uuid         primary key default gen_random_uuid(),
  user_id         uuid         not null references auth.users (id) on delete cascade,
  security_name   text         not null,                     -- e.g. 'NVIDIA', 'VOO (S&P 500)'
  shares          numeric(18,6),                             -- shares held (optional)
  amount_invested numeric(14,2),                             -- total $ put in (if shares unknown)
  cost_basis      numeric(14,4),                             -- avg price paid per share
  purchase_date   date,
  note            text,
  created_at      timestamptz  not null default now(),
  updated_at      timestamptz  not null default now()
);
comment on table public.holdings is 'A user''s portfolio positions. Current value + ROI computed at display time from live prices.';
create index if not exists holdings_user_idx on public.holdings (user_id);


-- 3) RISK_ANSWERS -----------------------------------------------------------
create table if not exists public.risk_answers (
  id            uuid        primary key default gen_random_uuid(),
  user_id       uuid        not null references auth.users (id) on delete cascade,
  time_horizon  text,                                        -- 'short' | 'mid' | 'long'
  risk_reaction text,                                        -- 'low'   | 'mid' | 'high'
  result        jsonb       not null default '{}'::jsonb,     -- the Buy/Maybe/Avoid picks shown
  snapshot_date date,                                         -- which data run it was based on
  created_at    timestamptz not null default now()
);
comment on table public.risk_answers is 'Each completed wizard: the two answers plus the result we generated.';
create index if not exists risk_answers_user_idx on public.risk_answers (user_id, created_at desc);


-- 4) WATCHLIST_ITEMS --------------------------------------------------------
create table if not exists public.watchlist_items (
  id            uuid        primary key default gen_random_uuid(),
  user_id       uuid        not null references auth.users (id) on delete cascade,
  security_name text        not null,
  note          text,
  added_at      timestamptz not null default now(),
  unique (user_id, security_name)
);
comment on table public.watchlist_items is 'Securities each user follows. One row per user+security.';
create index if not exists watchlist_user_idx on public.watchlist_items (user_id);


-- ============================================================================
--  SECURITY: Row Level Security — each user sees ONLY their own rows
-- ============================================================================
alter table public.profiles        enable row level security;
alter table public.holdings        enable row level security;
alter table public.risk_answers    enable row level security;
alter table public.watchlist_items enable row level security;

create policy "own profile - select" on public.profiles for select using (auth.uid() = id);
create policy "own profile - update" on public.profiles for update using (auth.uid() = id);

create policy "own holdings - select" on public.holdings for select using (auth.uid() = user_id);
create policy "own holdings - insert" on public.holdings for insert with check (auth.uid() = user_id);
create policy "own holdings - update" on public.holdings for update using (auth.uid() = user_id);
create policy "own holdings - delete" on public.holdings for delete using (auth.uid() = user_id);

create policy "own answers - select" on public.risk_answers for select using (auth.uid() = user_id);
create policy "own answers - insert" on public.risk_answers for insert with check (auth.uid() = user_id);
create policy "own answers - delete" on public.risk_answers for delete using (auth.uid() = user_id);

create policy "own watchlist - select" on public.watchlist_items for select using (auth.uid() = user_id);
create policy "own watchlist - insert" on public.watchlist_items for insert with check (auth.uid() = user_id);
create policy "own watchlist - delete" on public.watchlist_items for delete using (auth.uid() = user_id);


-- ============================================================================
--  AUTOMATION
-- ============================================================================
-- keep updated_at fresh
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();

drop trigger if exists holdings_set_updated_at on public.holdings;
create trigger holdings_set_updated_at before update on public.holdings
  for each row execute function public.set_updated_at();

-- auto-create a profile the moment someone signs up
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, new.raw_user_meta_data ->> 'full_name')
  on conflict (id) do nothing;
  return new;
end; $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================================
--  Done. Four tables, secured, with auto-profile-on-signup.
-- ============================================================================
