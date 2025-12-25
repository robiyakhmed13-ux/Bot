create table if not exists users (
  id bigserial primary key,
  telegram_id bigint unique not null,
  lang text not null default 'uz',
  created_at timestamptz not null default now()
);

create table if not exists transactions (
  id bigserial primary key,
  telegram_id bigint not null,
  type text not null check (type in ('expense','income','debt')),
  amount bigint not null check (amount >= 0),
  category_key text not null,
  description text,
  merchant text,
  occurred_at timestamptz not null default now(),
  source text not null default 'manual',
  raw_text text,
  created_at timestamptz not null default now()
);

create index if not exists idx_tx_user_date on transactions (telegram_id, occurred_at desc);

create table if not exists budgets (
  id bigserial primary key,
  telegram_id bigint not null,
  category_key text, -- null = overall monthly budget
  monthly_limit bigint not null check (monthly_limit >= 0),
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  unique (telegram_id, category_key)
);
