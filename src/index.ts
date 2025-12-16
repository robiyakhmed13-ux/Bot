// ============================================
// HAMYON - TELEGRAM BOT (TypeScript, Railway-ready)
// Smart Finance Tracker - ALL FEATURES FREE
// ============================================

import "dotenv/config";
import { Bot, InlineKeyboard } from "grammy";
import { createClient, SupabaseClient } from "@supabase/supabase-js";

// ----------------------------
// CONFIG
// ----------------------------
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN ?? "";
const SUPABASE_URL = process.env.SUPABASE_URL ?? "";
const SUPABASE_KEY = process.env.SUPABASE_ANON_KEY ?? "";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY ?? "";
const WEBAPP_URL = process.env.WEBAPP_URL ?? "https://t.me/hamyonmoneybot/app";

if (!BOT_TOKEN) throw new Error("Missing TELEGRAM_BOT_TOKEN");
if (!SUPABASE_URL) throw new Error("Missing SUPABASE_URL");
if (!SUPABASE_KEY) throw new Error("Missing SUPABASE_ANON_KEY");

const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_KEY);
const bot = new Bot(BOT_TOKEN);

// ----------------------------
// TYPES
// ----------------------------
type TxSource = "text" | "voice" | "receipt" | "app";
type TxInsert = {
  description: string;
  amount: number;
  categoryId: string;
  source: TxSource;
};

type TodayStats = { expenses: number; income: number; count: number };

type Category = {
  id: string;
  name: string;
  emoji: string;
  keywords: string[];
};

type CategoryDetect = {
  id: string;
  type: "expense" | "income";
  category: Category;
};

// ----------------------------
// CATEGORIES (your big list can stay; trimmed here for brevity)
// ----------------------------
const CATEGORIES: { expense: Category[]; income: Category[] } = {
  expense: [
    { id: "food", name: "Oziq-ovqat", emoji: "🍕", keywords: ["food", "grocery", "oziq", "ovqat", "korzinka", "makro"] },
    { id: "taxi", name: "Taksi", emoji: "🚕", keywords: ["taxi", "taksi", "yandex", "uber"] },
    { id: "coffee", name: "Kofe", emoji: "☕", keywords: ["coffee", "kofe", "tea", "choy"] },
    { id: "utilities", name: "Kommunal", emoji: "💡", keywords: ["utilities", "kommunal", "elektr", "tok", "suv", "gaz"] },
    { id: "other", name: "Boshqa", emoji: "📦", keywords: ["other", "boshqa", "turli"] }
  ],
  income: [
    { id: "salary", name: "Oylik maosh", emoji: "💰", keywords: ["salary", "oylik", "maosh", "ish haqi", "wage"] },
    { id: "bonus", name: "Bonus", emoji: "🎉", keywords: ["bonus", "premiya", "mukofot"] },
    { id: "other_income", name: "Boshqa daromad", emoji: "💵", keywords: ["income", "daromad", "pul keldi", "tushdi", "oldim"] }
  ]
};

// ----------------------------
// DB HELPERS
// ----------------------------
async function getOrCreateUser(telegramId: number, firstName: string, lastName?: string): Promise<any> {
  const { data: existing, error: e1 } = await supabase
    .from("users")
    .select("*")
    .eq("telegram_id", telegramId)
    .maybeSingle();

  if (e1) console.error("getOrCreateUser select error:", e1);
  if (existing) return existing;

  const { data: created, error: e2 } = await supabase
    .from("users")
    .insert({
      telegram_id: telegramId,
      name: `${firstName}${lastName ? " " + lastName : ""}`,
      balance: 0,
      created_at: new Date().toISOString()
    })
    .select()
    .single();

  if (e2) throw e2;
  return created;
}

async function getBalance(telegramId: number): Promise<number> {
  const { data, error } = await supabase
    .from("users")
    .select("balance")
    .eq("telegram_id", telegramId)
    .single();

  if (error) console.error("getBalance error:", error);
  return Number(data?.balance ?? 0);
}

async function saveTransaction(telegramId: number, tx: TxInsert): Promise<any> {
  const { data, error } = await supabase
    .from("transactions")
    .insert({
      user_telegram_id: telegramId,
      description: tx.description,
      amount: tx.amount,
      category_id: tx.categoryId,
      source: tx.source,
      created_at: new Date().toISOString()
    })
    .select()
    .single();

  if (error) throw error;

  // If you have RPC update_balance, keep it. If not, comment this out.
  const { error: rpcErr } = await supabase.rpc("update_balance", {
    p_telegram_id: telegramId,
    p_amount: tx.amount
  });
  if (rpcErr) console.error("update_balance rpc error:", rpcErr);

  return data;
}

async function getTodayStats(telegramId: number): Promise<TodayStats> {
  const today = new Date().toISOString().split("T")[0]; // YYYY-MM-DD
  const { data, error } = await supabase
    .from("transactions")
    .select("amount")
    .eq("user_telegram_id", telegramId)
    .gte("created_at", today);

  if (error) console.error("getTodayStats error:", error);

  let expenses = 0;
  let income = 0;
  for (const row of data ?? []) {
    const amount = Number((row as any).amount ?? 0);
    if (amount < 0) expenses += Math.abs(amount);
    else income += amount;
  }
  return { expenses, income, count: (data ?? []).length };
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

function detectCategory(text: string): CategoryDetect {
  const lower = text.toLowerCase();

  for (const cat of CATEGORIES.income) {
    if (cat.keywords.some((kw) => lower.includes(kw))) return { id: cat.id, type: "income", category: cat };
  }
  for (const cat of CATEGORIES.expense) {
    if (cat.keywords.some((kw) => lower.includes(kw))) return { id: cat.id, type: "expense", category: cat };
  }

  const other = CATEGORIES.expense.find((c) => c.id === "other")!;
  return { id: other.id, type: "expense", category: other };
}

function formatMoney(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1_000_000) return (amount / 1_000_000).toFixed(1).replace(".0", "") + "M UZS";
  return amount.toLocaleString("en-US").replace(/,/g, " ") + " UZS";
}

// ----------------------------
// OPENAI HELPERS (VOICE + RECEIPT)
// ----------------------------
async function transcribeVoice(fileUrl: string): Promise<string> {
  if (!OPENAI_API_KEY) return "";

  try {
    const audioResponse = await fetch(fileUrl);
    const audioBuffer = await audioResponse.arrayBuffer();

    const formData = new FormData();
    formData.append("file", new Blob([audioBuffer], { type: "audio/ogg" }), "voice.ogg");
    formData.append("model", "whisper-1");
    formData.append("language", "uz");

    const response = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
      body: formData
    });

    const result = (await response.json()) as any;
    return String(result?.text ?? "");
  } catch (e) {
    console.error("Whisper error:", e);
    return "";
  }
}

async function extractReceiptData(imageUrl: string): Promise<{ amount: number; store: string } | null> {
  if (!OPENAI_API_KEY) return null;

  try {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "gpt-4o",
        messages: [
          {
            role: "user",
            content: [
              { type: "text", text: `Chekdan umumiy summa va do'kon nomini ajrating. JSON: {"amount": number, "store": "string"}` },
              { type: "image_url", image_url: { url: imageUrl } }
            ]
          }
        ],
        max_tokens: 150
      })
    });

    const result = (await response.json()) as any;
    const content = String(result?.choices?.[0]?.message?.content ?? "");
    const jsonMatch = content.match(/\{[\s\S]*\}/);

    if (!jsonMatch) return null;
    const parsed = JSON.parse(jsonMatch[0]) as any;

    const amount = Number(parsed?.amount ?? 0);
    const store = String(parsed?.store ?? "Chek");
    if (!amount) return null;

    return { amount, store };
  } catch (e) {
    console.error("Vision error:", e);
    return null;
  }
}

// ----------------------------
// COMMANDS
// ----------------------------
bot.command("start", async (ctx) => {
  const from = ctx.from;
  if (!from) return;

  await getOrCreateUser(from.id, from.first_name, from.last_name);

  const keyboard = new InlineKeyboard().webApp("📊 Hamyon ilovasini ochish", WEBAPP_URL);

  await ctx.reply(
    `👋 Salom! Men Hamyon - moliyaviy yordamchingizman.\n\n` +
      `📱 *Tranzaksiya qo'shish usullari:*\n\n` +
      `🎤 *Ovozli xabar* - "Kofe 15 ming", "Taksi 30k"\n` +
      `💬 *Matn* - "Tushlik 45000"\n` +
      `📷 *Chek* - Chek rasmini yuboring\n\n` +
      `Barcha funksiyalar BEPUL! 🚀`,
    { parse_mode: "Markdown", reply_markup: keyboard }
  );
});

bot.command("balance", async (ctx) => {
  const from = ctx.from;
  if (!from) return;

  const bal = await getBalance(from.id);
  const today = await getTodayStats(from.id);
  const keyboard = new InlineKeyboard().webApp("📊 To'liq ilova", WEBAPP_URL);

  await ctx.reply(
    `💰 *Balans: ${formatMoney(bal)}*\n\n📅 Bugun:\n↘️ Xarajat: ${formatMoney(today.expenses)}\n↗️ Daromad: ${formatMoney(today.income)}`,
    { parse_mode: "Markdown", reply_markup: keyboard }
  );
});

bot.command("help", async (ctx) => {
  await ctx.reply(
    `🎙️ *Ovozli xabar:*\n1. Mikrofon tugmasini bosib turing\n2. "Kofe 15 ming" deb ayting\n3. Yuborish uchun qo'yib yuboring\n\n` +
      `💬 *Matn:* "Taksi 30000" deb yozing\n\n📷 *Chek:* Rasm yuboring`,
    { parse_mode: "Markdown" }
  );
});

// ----------------------------
// TEXT
// ----------------------------
bot.on("message:text", async (ctx) => {
  const from = ctx.from;
  const text = ctx.message?.text;
  if (!from || !text) return;
  if (text.startsWith("/")) return;

  const amount = parseAmount(text);
  if (!amount) {
    await ctx.reply(`❌ Summani aniqlab bo'lmadi.\n\n💡 Masalan: "Kofe 15000"`);
    return;
  }

  const { id: categoryId, type, category } = detectCategory(text);
  const finalAmount = type === "expense" ? -Math.abs(amount) : Math.abs(amount);

  await saveTransaction(from.id, { description: text, amount: finalAmount, categoryId, source: "text" });
  const bal = await getBalance(from.id);

  const keyboard = new InlineKeyboard().webApp("📊 Ilovani ochish", WEBAPP_URL);

  await ctx.reply(
    `✅ *Saqlandi!*\n\n${category.emoji} ${category.name}\n${type === "expense" ? "💸" : "💰"} ${formatMoney(Math.abs(finalAmount))}\n💰 Balans: ${formatMoney(bal)}`,
    { parse_mode: "Markdown", reply_markup: keyboard }
  );
});

// ----------------------------
// VOICE
// ----------------------------
bot.on("message:voice", async (ctx) => {
  const from = ctx.from;
  const voice = ctx.message?.voice;
  if (!from || !voice) return;

  await ctx.reply("🎤 Qayta ishlanmoqda...");

  try {
    const file = await ctx.api.getFile(voice.file_id);
    const fileUrl = `https://api.telegram.org/file/bot${BOT_TOKEN}/${file.file_path}`;

    const transcription = await transcribeVoice(fileUrl);
    if (!transcription) {
      await ctx.reply("❌ Tushunib bo'lmadi. Qayta urinib ko'ring.");
      return;
    }

    const amount = parseAmount(transcription);
    if (!amount) {
      await ctx.reply(`📝 Eshitdim: "${transcription}"\n\n❌ Summani aniqlab bo'lmadi.`);
      return;
    }

    const { id: categoryId, type, category } = detectCategory(transcription);
    const finalAmount = type === "expense" ? -Math.abs(amount) : Math.abs(amount);

    await saveTransaction(from.id, { description: transcription, amount: finalAmount, categoryId, source: "voice" });
    const bal = await getBalance(from.id);

    const keyboard = new InlineKeyboard().webApp("📊 Ilovani ochish", WEBAPP_URL);

    await ctx.reply(
      `✅ *Saqlandi!*\n\n${category.emoji} ${category.name}\n💸 ${formatMoney(Math.abs(finalAmount))}\n💰 Balans: ${formatMoney(bal)}`,
      { parse_mode: "Markdown", reply_markup: keyboard }
    );
  } catch (e) {
    console.error("Voice error:", e);
    await ctx.reply("❌ Xatolik yuz berdi.");
  }
});

// ----------------------------
// PHOTO (RECEIPT)
// ----------------------------
bot.on("message:photo", async (ctx) => {
  const from = ctx.from;
  const photo = ctx.message?.photo;
  if (!from || !photo?.length) return;

  await ctx.reply("📷 Skanerlanmoqda...");

  try {
    const file = await ctx.api.getFile(photo[photo.length - 1].file_id);
    const fileUrl = `https://api.telegram.org/file/bot${BOT_TOKEN}/${file.file_path}`;

    const receipt = await extractReceiptData(fileUrl);
    if (!receipt) {
      await ctx.reply("❌ Chekni o'qib bo'lmadi.");
      return;
    }

    const { id: categoryId, category } = detectCategory(receipt.store);
    await saveTransaction(from.id, {
      description: receipt.store,
      amount: -Math.abs(receipt.amount),
      categoryId,
      source: "receipt"
    });

    const bal = await getBalance(from.id);
    const keyboard = new InlineKeyboard().webApp("📊 Ilovani ochish", WEBAPP_URL);

    await ctx.reply(
      `✅ *Chek qabul qilindi!*\n\n🏪 ${receipt.store}\n💸 ${formatMoney(receipt.amount)}\n${category.emoji} ${category.name}\n💰 Balans: ${formatMoney(bal)}`,
      { parse_mode: "Markdown", reply_markup: keyboard }
    );
  } catch (e) {
    console.error("Photo error:", e);
    await ctx.reply("❌ Xatolik yuz berdi.");
  }
});

// ----------------------------
// START
// ----------------------------
bot.catch((err) => console.error("Bot error:", err));
console.log("🚀 Hamyon Bot ishga tushdi...");
bot.start();
