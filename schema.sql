-- USERS
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT UNIQUE NOT NULL,
  full_name TEXT,
  language TEXT DEFAULT 'uz',
  timezone TEXT DEFAULT 'Asia/Tashkent',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- CATEGORIES (you can extend)
CREATE TABLE IF NOT EXISTS categories (
  id BIGSERIAL PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,           -- e.g. "food"
  name TEXT NOT NULL,                -- e.g. "Oziq-ovqat"
  emoji TEXT DEFAULT '📦',
  type TEXT NOT NULL CHECK (type IN ('expense','income','debt'))
);

-- TRANSACTIONS
CREATE TABLE IF NOT EXISTS transactions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('expense','income','debt')),
  amount BIGINT NOT NULL CHECK (amount >= 0),
  category_key TEXT NOT NULL,
  description TEXT,
  source TEXT DEFAULT 'manual' CHECK (source IN ('manual','text','voice','receipt')),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tx_user_created ON transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tx_user_day ON transactions(user_id, (date(created_at)));

-- Seed categories (safe)
INSERT INTO categories(key,name,emoji,type) VALUES
('food','Oziq-ovqat','🍕','expense'),
('transport','Transport','🚕','expense'),
('rent','Ijara','🏠','expense'),
('salary','Oylik','💼','income')
ON CONFLICT (key) DO NOTHING;
