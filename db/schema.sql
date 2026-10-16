-- Watchlists and paper trades, private to each signed-in user (row-level security).
create table if not exists public.watchlists (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name       text not null,
  tickers    text[] not null default '{}',
  updated_at timestamptz not null default now(),
  primary key (user_id, name)
);

create table if not exists public.paper_trades (
  id          bigint primary key,
  user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
  ticker      text not null,
  market      text not null,
  currency    text,
  entry_date  date,
  entry_price numeric,
  entry_idx   numeric,
  label       text,
  hz          text[],
  flags       text[],
  score       numeric,
  amount      numeric,
  shares      numeric,
  note        text,
  status      text not null default 'open',
  exit_date   date,
  exit_price  numeric,
  exit_idx    numeric,
  exit_label  text,
  created_at  timestamptz not null default now()
);

alter table public.watchlists   enable row level security;
alter table public.paper_trades enable row level security;

drop policy if exists "own watchlists" on public.watchlists;
create policy "own watchlists" on public.watchlists
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists "own paper trades" on public.paper_trades;
create policy "own paper trades" on public.paper_trades
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());
