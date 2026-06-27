-- ============================================================================
--  RiskLens — saved Research chats (like Claude's chat history)
--  Run ONCE in Supabase: SQL Editor → New query → paste → Run.
-- ============================================================================

-- one row per conversation
create table if not exists public.conversations (
  id          uuid        primary key default gen_random_uuid(),
  user_id     uuid        not null references auth.users (id) on delete cascade,
  title       text        not null default 'New chat',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists conversations_user_idx on public.conversations (user_id, updated_at desc);

-- one row per message in a conversation
create table if not exists public.messages (
  id              uuid        primary key default gen_random_uuid(),
  conversation_id uuid        not null references public.conversations (id) on delete cascade,
  user_id         uuid        not null references auth.users (id) on delete cascade,
  role            text        not null,        -- 'user' | 'assistant'
  content         text        not null,
  created_at      timestamptz not null default now()
);
create index if not exists messages_convo_idx on public.messages (conversation_id, created_at);

-- security: users only see their own conversations + messages
alter table public.conversations enable row level security;
alter table public.messages      enable row level security;

create policy "own convos - select" on public.conversations for select using (auth.uid() = user_id);
create policy "own convos - insert" on public.conversations for insert with check (auth.uid() = user_id);
create policy "own convos - update" on public.conversations for update using (auth.uid() = user_id);
create policy "own convos - delete" on public.conversations for delete using (auth.uid() = user_id);

create policy "own messages - select" on public.messages for select using (auth.uid() = user_id);
create policy "own messages - insert" on public.messages for insert with check (auth.uid() = user_id);
create policy "own messages - delete" on public.messages for delete using (auth.uid() = user_id);

-- keep conversations.updated_at fresh
drop trigger if exists conversations_set_updated_at on public.conversations;
create trigger conversations_set_updated_at
  before update on public.conversations
  for each row execute function public.set_updated_at();

-- ============================================================================
--  Done. Two new tables: conversations, messages.
-- ============================================================================
