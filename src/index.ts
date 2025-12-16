// ============================================
// HAMYON - TELEGRAM BOT (Grammy + Supabase)
// Smart Finance Tracker - ALL FEATURES FREE
// ============================================

import "dotenv/config";
import { Bot, InlineKeyboard } from "grammy";
import { createClient } from "@supabase/supabase-js";

// ----------------------------
// CONFIG
// ----------------------------
const config = {
  BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN || "",
  SUPABASE_URL: process.env.SUPABASE_URL || "",
  SUPABASE_KEY: process.env.SUPABASE_ANON_KEY || "",
  OPENAI_API_KEY: process.env.OPENAI_API_KEY || "", // optional
  WEBAPP_URL: process.env.WEBAPP_URL || "https://t.me/hamyonmoneybot/app",
};

if (!config.BOT_TOKEN) throw new Error("Missing TELEGRAM_BOT_TOKEN");
if (!config.SUPABASE_URL) throw new Error("Missing SUPABASE_URL");
if (!config.SUPABASE_KEY) throw new Error("Missing SUPABASE_ANON_KEY");

const supabase = createClient(config.SUPABASE_URL, config.SUPABASE_KEY, {
  auth: { persistSession: false },
});
const bot = new Bot(config.BOT_TOKEN);

// ----------------------------
// CATEGORIES (your set)
// ----------------------------
const CATEGORIES = {
  expense: [
    { id: "food", name: "Oziq-ovqat", emoji: "🍕", keywords: ["food", "grocery", "oziq", "ovqat", "korzinka", "makro", "havas"] },
    { id: "restaurants", name: "Restoranlar", emoji: "🍽️", keywords: ["restaurant", "restoran", "lunch", "tushlik", "dinner", "kechki", "cafe", "caravan", "evos"] },
    { id: "coffee", name: "Kofe", emoji: "☕", keywords: ["coffee", "kofe", "tea", "choy", "starbucks", "drink"] },
    { id: "fastfood", name: "Fast Food", emoji: "🍔", keywords: ["fastfood", "burger", "pizza", "lavash", "shaurma", "mcdonalds", "kfc"] },
    { id: "delivery", name: "Yetkazib berish", emoji: "🛵", keywords: ["delivery", "yetkazib", "express24", "wolt", "glovo"] },
    { id: "taxi", name: "Taksi", emoji: "🚕", keywords: ["taxi", "taksi", "yandex", "uber", "mytaxi", "mashina"] },
    { id: "fuel", name: "Benzin", emoji: "⛽", keywords: ["fuel", "benzin", "gaz", "yonilgi", "zapravka"] },
    { id: "publicTransport", name: "Transport", emoji: "🚌", keywords: ["bus", "avtobus", "metro", "transport"] },
    { id: "parking", name: "Parkovka", emoji: "🅿️", keywords: ["parking", "parkovka", "toxtash"] },
    { id: "carMaintenance", name: "Avto xizmat", emoji: "🔧", keywords: ["car", "mashina", "avto", "remont", "yog", "service"] },
    { id: "clothing", name: "Kiyim", emoji: "👕", keywords: ["clothes", "kiyim", "koylak", "shim", "dress"] },
    { id: "electronics", name: "Elektronika", emoji: "📱", keywords: ["phone", "telefon", "laptop", "kompyuter", "texnika", "mediapark"] },
    { id: "accessories", name: "Aksessuarlar", emoji: "👜", keywords: ["bag", "sumka", "wallet", "hamyon", "watch", "soat"] },
    { id: "gifts", name: "Sovg'alar", emoji: "🎁", keywords: ["gift", "sovga", "hadya", "tuhfa", "present"] },
    { id: "beauty", name: "Go'zallik", emoji: "💄", keywords: ["beauty", "cosmetics", "kosmetika", "salon", "sartaroshxona"] },
    { id: "rent", name: "Ijara", emoji: "🏠", keywords: ["rent", "ijara", "kvartira", "uy", "apartment"] },
    { id: "utilities", name: "Kommunal", emoji: "💡", keywords: ["utilities", "kommunal", "elektr", "tok", "suv", "gaz"] },
    { id: "internet", name: "Internet", emoji: "📶", keywords: ["internet", "telefon", "beeline", "ucell", "mobiuz", "uzmobile"] },
    { id: "furniture", name: "Mebel", emoji: "🛋️", keywords: ["furniture", "mebel", "stol", "stul", "shkaf"] },
    { id: "repairs", name: "Ta'mirlash", emoji: "🔨", keywords: ["repair", "remont", "tamir", "qurilish"] },
    { id: "movies", name: "Kino", emoji: "🎬", keywords: ["movie", "kino", "film", "cinema", "imax"] },
    { id: "games", name: "O'yinlar", emoji: "🎮", keywords: ["game", "oyin", "playstation", "xbox", "steam"] },
    { id: "subscriptions", name: "Obunalar", emoji: "📺", keywords: ["subscription", "obuna", "netflix", "spotify", "youtube", "premium"] },
    { id: "concerts", name: "Konsertlar", emoji: "🎵", keywords: ["concert", "konsert", "festival", "event", "tadbir"] },
    { id: "hobbies", name: "Sevimli mashg'ulot", emoji: "🎨", keywords: ["hobby", "sevimli", "art", "craft"] },
    { id: "pharmacy", name: "Dorixona", emoji: "💊", keywords: ["pharmacy", "dorixona", "dori", "apteka", "medicine", "tabletka"] },
    { id: "doctor", name: "Shifokor", emoji: "🏥", keywords: ["doctor", "shifokor", "vrach", "hospital", "kasalxona", "clinic", "klinika"] },
    { id: "gym", name: "Sport zal", emoji: "💪", keywords: ["gym", "zal", "fitness", "fitnes", "trenirovka", "workout"] },
    { id: "sports", name: "Sport", emoji: "⚽", keywords: ["sport", "futbol", "football", "tennis", "suzish"] },
    { id: "wellness", name: "Sog'lomlik", emoji: "🧘", keywords: ["spa", "massage", "massaj", "sauna", "hammom"] },
    { id: "courses", name: "Kurslar", emoji: "📚", keywords: ["course", "kurs", "lesson", "dars", "talim", "education"] },
    { id: "books", name: "Kitoblar", emoji: "📖", keywords: ["book", "kitob", "oqish", "reading"] },
    { id: "tuition", name: "O'qish to'lovi", emoji: "🎓", keywords: ["tuition", "maktab", "universitet", "school", "tolov"] },
    { id: "supplies", name: "O'quv anjomlari", emoji: "✏️", keywords: ["supplies", "daftar", "ruchka", "stationery"] },
    { id: "flights", name: "Parvozlar", emoji: "✈️", keywords: ["flight", "parvoz", "samolyot", "bilet", "avia", "uzbekistan airways"] },
    { id: "hotels", name: "Mehmonxona", emoji: "🏨", keywords: ["hotel", "mehmonxona", "booking", "yashash"] },
    { id: "vacation", name: "Dam olish", emoji: "🏖️", keywords: ["vacation", "dam olish", "sayohat", "travel", "trip"] },
    { id: "businessTravel", name: "Xizmat safari", emoji: "💼", keywords: ["business trip", "komandirovka", "xizmat safari"] },
    { id: "pets", name: "Uy hayvonlari", emoji: "🐕", keywords: ["pet", "hayvon", "it", "mushuk", "dog", "cat", "vet"] },
    { id: "charity", name: "Xayriya", emoji: "❤️", keywords: ["charity", "xayriya", "sadaqa", "yordam", "donation"] },
    { id: "insurance", name: "Sug'urta", emoji: "🛡️", keywords: ["insurance", "sugurta"] },
    { id: "taxes", name: "Soliqlar", emoji: "📋", keywords: ["tax", "soliq", "nalog"] },
    { id: "childcare", name: "Bolalar", emoji: "👶", keywords: ["baby", "bola", "child", "kids", "bogcha", "daycare"] },
    { id: "other", name: "Boshqa", emoji: "📦", keywords: ["other", "boshqa", "turli"] },
  ],
  income: [
    { id: "salary", name: "Oylik maosh", emoji: "💰", keywords: ["salary", "oylik", "maosh", "ish haqi", "wage", "pay"] },
    { id: "freelance", name: "Frilanser", emoji: "💻", keywords: ["freelance", "frilanser", "project", "loyiha"] },
    { id: "business", name: "Biznes", emoji: "🏢", keywords: ["business", "biznes", "profit", "foyda", "tushum"] },
    { id: "investments", name: "Investitsiya", emoji: "📈", keywords: ["investment", "investitsiya", "dividend", "aksiya"] },
    { id: "rental", name: "Ijara daromadi", emoji: "🏘️", keywords: ["rental income", "ijara daromadi", "ijaraga"] },
    { id: "gifts_income", name: "Sovg'a olindi", emoji: "🎀", keywords: ["gift received", "sovga oldim", "hadya"] },
    { id: "refunds", name: "Qaytarilgan pul", emoji: "↩️", keywords: ["refund", "return", "qaytarish", "vozvrat"] },
    { id: "bonus", name: "Bonus", emoji: "🎉", keywords: ["bonus", "premiya", "mukofot"] },
    { id: "cashback", name: "Keshbek", emoji: "💳", keywords: ["cashback", "keshbek", "qaytim"] },
    { id: "other_income", name: "Boshqa daromad", emoji: "💵", keywords: ["income", "daromad", "pul keldi", "tushdi", "oldim"] },
  ],
};

// ----------------------------
// UTIL
// ----------------------------
function formatMoney(amount) {
  const abs = Math.abs(Number(amount || 0));
  if (abs >= 1_000_000) return `${(amount / 1_000_000).toFixed(1).replace(".0", "")}M UZS`;
  return Number(amount || 0).toLocaleString("en-US").replace(/,/g, " ") + " UZS";
}

function parseAmount(text) {
  const lower = (text || "").toLowerCase();

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

function detectCategory(text) {
  const lower = (text || "").toLowerCase();

  for (const cat of CATEGORIES.income) {
    for (const kw of cat.keywords) {
      if (lower.includes(kw)) return { id: cat.id, type: "income", category: cat };
    }
  }
  for (const cat of CATEGORIES.expense) {
    for (const kw of cat.keywords) {
      if (lower.includes(kw)) return { id: cat.id, type: "expense", category: cat };
    }
  }
  const fallback = CATEGORIES.expense.find((c) => c.id === "other") || CATEGORIES.expense[0];
  return { id: fallback.id, type: "expense", category: fallback };
}

function getStartEndOfTodayISO() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0);
  return { startISO: start.toISOString(), endISO: end.toISOString() };
}

function webappKeyboard() {
  return new InlineKeyboard().webApp("📊 Hamyon ilovasini ochish", config.WEBAPP_URL);
}

// ----------------------------
// DB HELPERS
// ----------------------------
async function getOrCreateUser(telegramId, firstName, lastName) {
  const { data: existing, error: exErr } = await supabase
    .from("users")
    .select("*")
    .eq("telegram_id", telegramId)
    .maybeSingle();

  if (exErr) throw exErr;
  if (existing) return existing;

  const { data: created, error: crErr } = await supabase
    .from("users")
    .insert({
      telegram_id: telegramId,
      name: `${firstName}${lastName ? " " + lastName : ""}`.trim(),
      balance: 0,
      created_at: new Date().toISOString(),
    })
    .select()
    .single();

  if (crErr) throw crErr;
  return created;
}

async function getBalance(telegramId) {
  const { data, error } = await supabase
    .from("users")
    .select("balance")
    .eq("telegram_id", telegramId)
    .maybeSingle();

  if (error) throw error;
  return Number(data?.balance || 0);
}

async function updateBalanceBestEffort(telegramId, amount) {
  // 1) Try RPC if you have it
  const { error: rpcErr } = await supabase.rpc("update_balance", {
    p_telegram_id: telegramId,
    p_amount: amount,
  });

  if (!rpcErr) return;

  // 2) Fallback: read current balance then update (works without RPC)
  const current = await getBalance(telegramId);
  const next = current + Number(amount || 0);

  const { error: updErr } = await supabase
    .from("users")
    .update({ balance: next, updated_at: new Date().toISOString() })
    .eq("telegram_id", telegramId);

  if (updErr) throw updErr;
}

async function saveTransaction(telegramId, tx) {
  const payload = {
    user_telegram_id: telegramId,
    description: tx.description || "",
    amount: Number(tx.amount || 0),
    category_id: tx.categoryId || "other",
    source: tx.source || "text",
    created_at: new Date().toISOString(),
  };

  const { data, error } = await supabase
    .from("transactions")
    .insert(payload)
    .select()
    .single();

  if (error) throw error;

  await updateBalanceBestEffort(telegramId, payload.amount);
  return data;
}

async function getTodayStats(telegramId) {
  const { startISO, endISO } = getStartEndOfTodayISO();

  const { data, error } = await supabase
    .from("transactions")
    .select("amount")
    .eq("user_telegram_id", telegramId)
    .gte("created_at", startISO)
    .lt("created_at", endISO);

  if (error) throw error;

  let expenses = 0;
  let income = 0;
  for (const row of data || []) {
    const a = Number(row.amount || 0);
    if (a < 0) expenses += Math.abs(a);
    else income += a;
  }
  return { expenses, income, count: (data || []).length };
}

// ----------------------------
// OPENAI HELPERS (OPTIONAL)
// ----------------------------
async function transcribeVoice(fileUrl) {
  if (!config.OPENAI_API_KEY) return "";

  try {
    const audioRes = await fetch(fileUrl);
    if (!audioRes.ok) return "";
    const audioBuffer = await audioRes.arrayBuffer();

    const formData = new FormData();
    formData.append("file", new Blob([audioBuffer], { type: "audio/ogg" }), "voice.ogg");
    formData.append("model", "whisper-1");
    formData.append("language", "uz");

    const res = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: `Bearer ${config.OPENAI_API_KEY}` },
      body: formData,
    });

    const json = await res.json().catch(() => ({}));
    return (json.text || "").trim();
  } catch (e) {
    console.error("Whisper error:", e);
    return "";
  }
}

async function extractReceiptData(imageUrl) {
  if (!config.OPENAI_API_KEY) return null;

  try {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${config.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text:
                  "Chek rasmini ko'rib, umumiy summa va do'kon nomini qaytaring. " +
                  'Faqat JSON qaytaring: {"amount": number, "store": string}. Agar topilmasa {"amount":0,"store":""}.',
              },
              { type: "image_url", image_url: { url: imageUrl } },
            ],
          },
        ],
        max_tokens: 200,
      }),
    });

    const json = await res.json().catch(() => ({}));
    const content = json?.choices?.[0]?.message?.content || "";

    const match = content.match(/\{[\s\S]*\}/);
    if (!match) return null;

    const parsed = JSON.parse(match[0]);
    const amount = Number(parsed.amount || 0);
    const store = String(parsed.store || "").trim();
    if (!amount || amount <= 0) return null;

    return { amount, store: store || "Chek" };
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

  await ctx.reply(
    `👋 Salom! Men *Hamyon* — moliyaviy yordamchingiz.\n\n` +
      `📱 *Tranzaksiya qo'shish:*\n` +
      `🎤 Ovoz: "Kofe 15 ming", "Taksi 30k"\n` +
      `💬 Matn: "Tushlik 45000"\n` +
      `📷 Chek: chek rasmini yuboring\n\n` +
      `✅ Barcha funksiyalar bepul!`,
    { parse_mode: "Markdown", reply_markup: webappKeyboard() }
  );
});

bot.command("balance", async (ctx) => {
  const from = ctx.from;
  if (!from) return;

  await getOrCreateUser(from.id, from.first_name, from.last_name);

  const bal = await getBalance(from.id);
  const today = await getTodayStats(from.id);

  await ctx.reply(
    `💰 *Balans:* ${formatMoney(bal)}\n\n` +
      `📅 *Bugun:*\n` +
      `↘️ Xarajat: ${formatMoney(today.expenses)}\n` +
      `↗️ Daromad: ${formatMoney(today.income)}\n` +
      `🧾 Tranzaksiyalar: ${today.count}`,
    { parse_mode: "Markdown", reply_markup: webappKeyboard() }
  );
});

bot.command("help", async (ctx) => {
  await ctx.reply(
    `🎙️ *Ovozli xabar:*\n` +
      `1) Mikrofonni bosib turing\n` +
      `2) "Kofe 15 ming" deb ayting\n` +
      `3) Yuboring\n\n` +
      `💬 *Matn:* "Taksi 30000"\n` +
      `📷 *Chek:* rasm yuboring`,
    { parse_mode: "Markdown" }
  );
});

// ----------------------------
// VOICE HANDLER
// ----------------------------
bot.on("message:voice", async (ctx) => {
  const from = ctx.from;
  const voice = ctx.message?.voice;
  if (!from || !voice) return;

  await getOrCreateUser(from.id, from.first_name, from.last_name);

  await ctx.reply("🎤 Qayta ishlanmoqda...");

  try {
    const file = await ctx.api.getFile(voice.file_id);
    const fileUrl = `https://api.telegram.org/file/bot${config.BOT_TOKEN}/${file.file_path}`;

    const transcription = await transcribeVoice(fileUrl);
    if (!transcription) {
      await ctx.reply("❌ Tushunib bo'lmadi. Qayta urinib ko'ring.");
      return;
    }

    const amount = parseAmount(transcription);
    const { id: categoryId, type, category } = detectCategory(transcription);

    if (!amount) {
      await ctx.reply(`📝 Eshitdim: "${transcription}"\n\n❌ Summani aniqlab bo'lmadi.`);
      return;
    }

    const finalAmount = type === "expense" ? -Math.abs(amount) : Math.abs(amount);

    await saveTransaction(from.id, {
      description: transcription,
      amount: finalAmount,
      categoryId,
      source: "voice",
    });

    const bal = await getBalance(from.id);

    await ctx.reply(
      `✅ *Saqlandi!*\n\n` +
        `${category.emoji} ${category.name}\n` +
        `💸 ${formatMoney(Math.abs(finalAmount))}\n` +
        `💰 Balans: ${formatMoney(bal)}`,
      { parse_mode: "Markdown", reply_markup: webappKeyboard() }
    );
  } catch (e) {
    console.error("Voice error:", e);
    await ctx.reply("❌ Xatolik yuz berdi (voice).");
  }
});

// ----------------------------
// PHOTO HANDLER (RECEIPT)
// ----------------------------
bot.on("message:photo", async (ctx) => {
  const from = ctx.from;
  const photo = ctx.message?.photo;
  if (!from || !photo?.length) return;

  await getOrCreateUser(from.id, from.first_name, from.last_name);

  await ctx.reply("📷 Skanerlanmoqda...");

  try {
    const best = photo[photo.length - 1];
    const file = await ctx.api.getFile(best.file_id);
    const fileUrl = `https://api.telegram.org/file/bot${config.BOT_TOKEN}/${file.file_path}`;

    const receipt = await extractReceiptData(fileUrl);
    if (!receipt) {
      await ctx.reply("❌ Chekni o'qib bo'lmadi (yoki OpenAI yoqilmagan).");
      return;
    }

    const { id: categoryId, category } = detectCategory(receipt.store);

    await saveTransaction(from.id, {
      description: receipt.store,
      amount: -Math.abs(receipt.amount),
      categoryId,
      source: "receipt",
    });

    const bal = await getBalance(from.id);

    await ctx.reply(
      `✅ *Chek qabul qilindi!*\n\n` +
        `🏪 ${receipt.store}\n` +
        `💸 ${formatMoney(receipt.amount)}\n` +
        `${category.emoji} ${category.name}\n` +
        `💰 Balans: ${formatMoney(bal)}`,
      { parse_mode: "Markdown", reply_markup: webappKeyboard() }
    );
  } catch (e) {
    console.error("Photo error:", e);
    await ctx.reply("❌ Xatolik yuz berdi (photo).");
  }
});

// ----------------------------
// TEXT HANDLER
// ----------------------------
bot.on("message:text", async (ctx) => {
  const from = ctx.from;
  const text = ctx.message?.text;
  if (!from || !text) return;
  if (text.startsWith("/")) return;

  await getOrCreateUser(from.id, from.first_name, from.last_name);

  const amount = parseAmount(text);
  const { id: categoryId, type, category } = detectCategory(text);

  if (!amount) {
    await ctx.reply(`❌ Summani aniqlab bo'lmadi.\n\n💡 Masalan: "Kofe 15000" yoki "Taksi 30k"`);
    return;
  }

  const finalAmount = type === "expense" ? -Math.abs(amount) : Math.abs(amount);

  try {
    await saveTransaction(from.id, {
      description: text,
      amount: finalAmount,
      categoryId,
      source: "text",
    });

    const bal = await getBalance(from.id);

    await ctx.reply(
      `✅ *Saqlandi!*\n\n` +
        `${category.emoji} ${category.name}\n` +
        `${type === "expense" ? "💸" : "💰"} ${formatMoney(Math.abs(finalAmount))}\n` +
        `💰 Balans: ${formatMoney(bal)}`,
      { parse_mode: "Markdown", reply_markup: webappKeyboard() }
    );
  } catch (e) {
    console.error("Text save error:", e);
    await ctx.reply("❌ Xatolik yuz berdi (save). Supabase/RLS ni tekshiring.");
  }
});

// ----------------------------
// START
// ----------------------------
bot.catch((err) => console.error("Bot error:", err));
console.log("🚀 Hamyon Bot ishga tushdi...");
bot.start();
