-- ============================================================================
--  Market Analyst — track SOLD positions (realized profit)
--  Run ONCE in Supabase: SQL Editor → New query → paste → Run.
--
--  When a user sells a stock or option, we move it here and record the
--  profit they locked in — so it stays on their record permanently.
-- ============================================================================

create table if not exists public.closed_positions (
  id              uuid        primary key default gen_random_uuid(),
  user_id         uuid        not null references auth.users (id) on delete cascade,
  asset_type      text        not null,            -- 'stock' | 'option'
  name            text        not null,            -- what was sold (e.g. 'NVIDIA' or 'NVIDIA call $220 exp 2026-12-19')
  quantity        numeric(18,6),                    -- shares (stock) or contracts (option)
  cost_total      numeric(14,2),                    -- what they originally paid (total)
  proceeds_total  numeric(14,2),                    -- what they sold it for (total)
  realized        numeric(14,2),                    -- locked-in profit = proceeds - cost
  sold_date       date,
  created_at      timestamptz not null default now()
);
comment on table public.closed_positions is 'History of sold stocks/options + the realized (locked-in) profit on each.';
create index if not exists closed_positions_user_idx on public.closed_positions (user_id, sold_date desc);

alter table public.closed_positions enable row level security;
create policy "own closed - select" on public.closed_positions for select using (auth.uid() = user_id);
create policy "own closed - insert" on public.closed_positions for insert with check (auth.uid() = user_id);
create policy "own closed - delete" on public.closed_positions for delete using (auth.uid() = user_id);

-- ============================================================================
--  Done. One new table: closed_positions.
-- ============================================================================
