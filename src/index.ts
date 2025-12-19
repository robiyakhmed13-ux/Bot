// ============================================
// HAMYON - TELEGRAM BOT (TypeScript, Railway-ready)
// Smart Finance Tracker - ALL FEATURES FREE
// ============================================

import { Bot, InlineKeyboard, Context } from "grammy";
import { createClient, SupabaseClient } from "@supabase/supabase-js";
import "dotenv/config";

// ----------------------------
// CONFIG
// ----------------------------
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN ?? "";
const SUPABASE_URL = process.env.SUPABASE_URL ?? "";
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY ?? "";
const WEBAPP_URL = process.env.WEBAPP_URL ?? "https://t.me/hamyonmoneybot/";

if (!BOT_TOKEN) throw new Error("Missing TELEGRAM_BOT_TOKEN");
if (!SUPABASE_URL) throw new Error("Missing SUPABASE_URL");
if (!SUPABASE_KEY) throw new Error("Missing SUPABASE_ANON_KEY");

const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_KEY);
const bot = new Bot(BOT_TOKEN);

// ----------------------------
// TYPES
// ----------------------------
type Category = { id: string; name: string; emoji: string; keywords: string[] };
type CategoryDetect = { id: string; type: "expense" | "income"; category: Category };

type TxInsert = {
  description: string;
  amount: number; // negative = expense
  categoryId: string;
  source: "voice" | "text" | "receipt" | "manual";
};

type TodayStats = { expenses: number; income: number; count: number };

type UserRow = {
  telegram_id: number;
  name: string;
  balance: number | null;
};

// ----------------------------
// CATEGORIES (short demo - keep your full list)
// ----------------------------
const CATEGORIES: { expense: Category[]; income: Category[] } = {
  expense: [
    { id: "accessories", name: "Aksessuarlar", emoji: "👜", keywords: ["bag", "sumka", "wallet", "hamyon", "watch", "soat"] },
    { id: "food", name: "Oziq-ovqat", emoji: "🍕", keywords: ["food", "grocery", "oziq", "ovqat"] },
    { id: "taxi", name: "Taksi", emoji: "🚕", keywords: ["taxi", "taksi", "yandex"] },
    { id: "other", name: "Boshqa", emoji: "📦", keywords: ["other", "boshqa"] }
  ],
  income: [
    { id: "salary", name: "Oylik maosh", emoji: "💰", keywords: ["salary", "oylik", "maosh"] },
    { id: "other_income", name: "Boshqa daromad", emoji: "💵", keywords: ["income", "daromad"] }
  ]
};

// If you have 45+ categories, paste them here.
// IMPORTANT: categoryId in transactions must be VARCHAR(50) like "accessories".

function getCategoryById(id: string): Category {
  const all = [...CATEGORIES.expense, ...CATEGORIES.income];
  return all.find((c) => c.id === id) ?? { id: "other", name: "Boshqa", emoji: "📦", keywords: [] };
}

// ----------------------------
// DB HELPERS (match your schema)
// ----------------------------
async function getOrCreateUser(telegramId: number, firstName: string, lastName?: string): Promise<UserRow> {
  const { data: existing, error: e1 } = await supabase
    .from("users")
    .select("telegram_id,name,balance")
    .eq("telegram_id", telegramId)
    .maybeSingle<UserRow>();

  if (e1) console.error("getOrCreateUser select error:", e1);
  if (existing) return existing;

  const name = `${firstName}${lastName ? " " + lastName : ""}`;
  const { data: created, error: e2 } = await supabase
    .from("users")
    .insert({ telegram_id: telegramId, name })
    .select("telegram_id,name,balance")
    .single<UserRow>();

  if (e2) throw e2;
  return created;
}

async function getBalance(telegramId: number): Promise<number> {
  const { data, error } = await supabase
    .from("users")
    .select("balance")
    .eq("telegram_id", telegramId)
    .single<{ balance: number | null }>();

  if (error) console.error("getBalance error:", error);
  return Number(data?.balance ?? 0);
}

async function saveTransaction(telegramId: number, tx: TxInsert): Promise<void> {
  const { error } = await supabase.from("transactions").insert({
    user_telegram_id: telegramId,
    description: tx.description,
    amount: tx.amount,
    category_id: tx.categoryId,
    source: tx.source
  });

  if (error) throw error;

  // ✅ your SQL defines this
  const { error: rpcErr } = await supabase.rpc("update_balance", {
    p_telegram_id: telegramId,
    p_amount: Math.trunc(tx.amount)
  });
  if (rpcErr) console.error("update_balance rpc error:", rpcErr);
}

async function getTodayStats(telegramId: number): Promise<TodayStats> {
  const { data, error } = await supabase.rpc("get_today_stats", {
    p_telegram_id: telegramId
  }) as { data: { total_expenses: number; total_income: number; transaction_count: number }[] | null; error: unknown };

  if (error) console.error("get_today_stats error:", error);

  const row = data?.[0];
  return {
    expenses: Number(row?.total_expenses ?? 0),
    income: Number(row?.total_income ?? 0),
    count: Number(row?.transaction_count ?? 0)
  };
}

// ----------------------------
// PARSING
// ----------------------------
function parseAmount(text: string): number | null {
  const lower = text.toLowerCase();

  const millionMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(?:mln|million|миллион|млн)\b/i);
  if (millionMatch) return parseFloat(millionMatch[1].replace(",", ".")) * 1_000_000;

  const mMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*m(?!ing)\b/i);
  if (mMatch) return parseFloat(mMatch[1].replace(",", ".")) * 1_000_000;

  const kMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(?:k|к|тысяч|ming|минг)\b/i);
  if (kMatch) return parseFloat(kMatch[1].replace(",", ".")) * 1_000;

  const formattedMatch = text.match(/(\d{1,3}(?:[,\s]\d{3})+)/);
  if (formattedMatch) return parseInt(formattedMatch[1].replace(/[,\s]/g, ""), 10);

  const simpleMatch = text.match(/(\d+)/);
  if (simpleMatch) {
    const n = parseInt(simpleMatch[1], 10);
    if (n >= 100) return n;
  }
  return null;
}

function formatMoney(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1_000_000) return (amount / 1_000_000).toFixed(1).replace(".0", "") + "M UZS";
  return Math.trunc(amount).toLocaleString("en-US").replace(/,/g, " ") + " UZS";
}

function detectCategory(text: string): CategoryDetect {
  const lower = text.toLowerCase();

  for (const cat of CATEGORIES.income) {
    if (cat.keywords.some((kw) => lower.includes(kw))) return { id: cat.id, type: "income", category: cat };
  }
  for (const cat of CATEGORIES.expense) {
    if (cat.keywords.some((kw) => lower.includes(kw))) return { id: cat.id, type: "expense", category: cat };
  }
  const other = getCategoryById("other");
  return { id: other.id, type: "expense", category: other };
}

// ----------------------------
// CATEGORY → AMOUNT FLOW (what you asked)
// ----------------------------
const pendingCategory = new Map<number, { categoryId: string; type: "expense" | "income" }>();

bot.command("start", async (ctx: Context) => {
  const from = ctx.from;
  if (!from) return;

  await getOrCreateUser(from.id, from.first_name, from.last_name);

  const kb = new InlineKeyboard()
    .webApp("📊 Ilovani ochish", WEBAPP_URL)
    .row()
    .text("➖ Xarajat qo‘shish", "open_expenses")
    .text("➕ Daromad qo‘shish", "open_income");

  await ctx.reply(
    `👋 Salom! Hamyon bot.\n\n` +
      `✅ Eng oson usul:\n` +
      `1) Kategoriya tanlang\n` +
      `2) Summani yuboring (500000 yoki 500k)\n\n` +
      `Yoki matn yozing: "Taksi 30000"`,
    { reply_markup: kb }
  );
});

bot.command("balance", async (ctx: Context) => {
  const from = ctx.from;
  if (!from) return;

  const bal = await getBalance(from.id);
  const today = await getTodayStats(from.id);

  await ctx.reply(
    `💰 Balans: *${formatMoney(bal)}*\n\n📅 Bugun:\n↘️ Xarajat: ${formatMoney(today.expenses)}\n↗️ Daromad: ${formatMoney(today.income)}\n🧾 Tranzaksiyalar: ${today.count}`,
    { parse_mode: "Markdown" }
  );
});

// open expense picker
bot.callbackQuery("open_expenses", async (ctx) => {
  const kb = new InlineKeyboard();
  for (const c of CATEGORIES.expense) kb.text(`${c.emoji} ${c.name}`, `pick_exp:${c.id}`).row();
  await ctx.answerCallbackQuery();
  await ctx.reply("🧾 Xarajat kategoriyasini tanlang:", { reply_markup: kb });
});

// open income picker
bot.callbackQuery("open_income", async (ctx) => {
  const kb = new InlineKeyboard();
  for (const c of CATEGORIES.income) kb.text(`${c.emoji} ${c.name}`, `pick_inc:${c.id}`).row();
  await ctx.answerCallbackQuery();
  await ctx.reply("💰 Daromad kategoriyasini tanlang:", { reply_markup: kb });
});

// pick expense category
bot.callbackQuery(/^pick_exp:(.+)$/i, async (ctx) => {
  const from = ctx.from;
  if (!from) return;
  const categoryId = String(ctx.match[1]);
  pendingCategory.set(from.id, { categoryId, type: "expense" });

  const cat = getCategoryById(categoryId);
  await ctx.answerCallbackQuery();
  await ctx.reply(`✅ ${cat.emoji} ${cat.name}\n\nEndi summani yuboring.\nMasalan: 500000 yoki 500k`);
});

// pick income category
bot.callbackQuery(/^pick_inc:(.+)$/i, async (ctx) => {
  const from = ctx.from;
  if (!from) return;
  const categoryId = String(ctx.match[1]);
  pendingCategory.set(from.id, { categoryId, type: "income" });

  const cat = getCategoryById(categoryId);
  await ctx.answerCallbackQuery();
  await ctx.reply(`✅ ${cat.emoji} ${cat.name}\n\nEndi summani yuboring.\nMasalan: 2m yoki 1500000`);
});

// text handler
bot.on("message:text", async (ctx: Context) => {
  const from = ctx.from;
  const text = ctx.message?.text;
  if (!from || !text) return;
  if (text.startsWith("/")) return;

  // ✅ If user already picked category → treat text as amount only
  const pending = pendingCategory.get(from.id);
  if (pending) {
    const amount = parseAmount(text);
    if (!amount) {
      await ctx.reply("❌ Summani aniqlab bo'lmadi. Masalan: 500000 yoki 500k");
      return;
    }

    const finalAmount = pending.type === "expense" ? -Math.abs(amount) : Math.abs(amount);
    const cat = getCategoryById(pending.categoryId);

    await saveTransaction(from.id, {
      description: cat.name,
      amount: finalAmount,
      categoryId: pending.categoryId,
      source: "manual"
    });

    pendingCategory.delete(from.id);

    const bal = await getBalance(from.id);
    await ctx.reply(
      `✅ Saqlandi!\n\n${cat.emoji} ${cat.name}\n${pending.type === "expense" ? "💸" : "💰"} ${formatMoney(Math.abs(finalAmount))}\n💰 Balans: ${formatMoney(bal)}`
    );
    return;
  }

  // Otherwise, allow "Accessories 500000" style
  const amount = parseAmount(text);
  if (!amount) {
    await ctx.reply("❌ Summani aniqlab bo'lmadi.\nMasalan: 'Taksi 30000' yoki avval kategoriya tanlang.");
    return;
  }

  const { id: categoryId, type, category } = detectCategory(text);
  const finalAmount = type === "expense" ? -Math.abs(amount) : Math.abs(amount);

  await saveTransaction(from.id, {
    description: text,
    amount: finalAmount,
    categoryId,
    source: "text"
  });

  const bal = await getBalance(from.id);
  await ctx.reply(
    `✅ Saqlandi!\n\n${category.emoji} ${category.name}\n${type === "expense" ? "💸" : "💰"} ${formatMoney(Math.abs(finalAmount))}\n💰 Balans: ${formatMoney(bal)}`
  );
});

// ----------------------------
// START
// ----------------------------
bot.catch((err) => console.error("Bot error:", err));
console.log("🚀 Hamyon Bot ishga tushdi...");
bot.start();

