-- ============================================================================
--  Market Analyst — shared "searched stocks" cache
--  When anyone searches a stock that's not on the ranked list, the model's
--  quick estimate is saved here so EVERY user gets it instantly next time, and
--  the searches build into a browsable list. These are AI estimates (not the
--  full 150k-path simulation), kept separate from the core ranked universe.
--  Run ONCE in Supabase: SQL Editor → New query → paste → Run.
-- ============================================================================

create table if not exists public.stock_lookups (
  ticker      text        primary key,
  name        text,
  price       numeric,
  tier        text,
  growth      numeric,
  p25         numeric,
  rec2y       numeric,
  tail        numeric,
  vssp        numeric,
  verdict     text,
  explanation text,
  hits        int         not null default 1,
  updated_at  timestamptz not null default now()
);
create index if not exists stock_lookups_recent_idx on public.stock_lookups (updated_at desc);

-- This is a PUBLIC cache of model estimates (no private user data), so anyone —
-- signed in or not — can read it and add to it.
alter table public.stock_lookups enable row level security;

drop policy if exists "lookups public read"   on public.stock_lookups;
drop policy if exists "lookups public insert" on public.stock_lookups;
drop policy if exists "lookups public update" on public.stock_lookups;

create policy "lookups public read"   on public.stock_lookups for select using (true);
create policy "lookups public insert" on public.stock_lookups for insert with check (true);
create policy "lookups public update" on public.stock_lookups for update using (true);

-- ============================================================================
--  Done. One new table: stock_lookups (public, shared).
-- ============================================================================
