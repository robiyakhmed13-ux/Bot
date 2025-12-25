create table if not exists users (
  id bigserial primary key,
  telegram_id bigint unique not null,
  language text not null default 'uz',
  created_at timestamptz not null default now()
);

create table if not exists transactions (
  id uuid primary key default gen_random_uuid(),
  telegram_id bigint not null,
  type text not null check (type in ('expense','income','debt')),
  amount bigint not null check (amount >= 0),
  category_key text not null,
  description text,
  merchant text,
  tx_date date,
  source text not null default 'text',
  created_at timestamptz not null default now()
);

create index if not exists idx_transactions_tg_time
on transactions (telegram_id, created_at desc);

create index if not exists idx_transactions_tg_date
on transactions (telegram_id, tx_date desc);
