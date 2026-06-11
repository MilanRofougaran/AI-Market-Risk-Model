-- ============================================================================
--  Market Analyst — add OPTION POSITIONS to the portfolio
--  Run ONCE in Supabase: SQL Editor → New query → paste → Run.
--  (The "destructive operation" warning is fine — it only re-creates a trigger.)
--
--  Stores the option trades a user holds (calls/puts), separate from stocks.
-- ============================================================================

create table if not exists public.option_positions (
  id            uuid        primary key default gen_random_uuid(),
  user_id       uuid        not null references auth.users (id) on delete cascade,
  underlying    text        not null,                 -- the stock/fund the option is on (e.g. 'NVIDIA')
  kind          text        not null default 'call',  -- 'call' (bet up) | 'put' (bet down)
  strike        numeric(14,4),                         -- the strike price, in dollars
  expiry        date,                                  -- when the option expires
  contracts     numeric(10,2) default 1,               -- # of contracts (1 contract = 100 shares)
  premium_paid  numeric(14,4),                          -- what you paid per share (broker price)
  note          text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
comment on table public.option_positions is 'Option trades a user holds. Total cost = premium_paid × 100 × contracts.';
create index if not exists option_positions_user_idx on public.option_positions (user_id);

-- security: each user sees only their own option positions
alter table public.option_positions enable row level security;
create policy "own options - select" on public.option_positions for select using (auth.uid() = user_id);
create policy "own options - insert" on public.option_positions for insert with check (auth.uid() = user_id);
create policy "own options - update" on public.option_positions for update using (auth.uid() = user_id);
create policy "own options - delete" on public.option_positions for delete using (auth.uid() = user_id);

-- keep updated_at fresh
drop trigger if exists option_positions_set_updated_at on public.option_positions;
create trigger option_positions_set_updated_at
  before update on public.option_positions
  for each row execute function public.set_updated_at();

-- ============================================================================
--  Done. One new table: option_positions.
-- ============================================================================
