// ============================================
// HAMYON - TELEGRAM BOT
// Smart Finance Tracker - ALL FEATURES FREE
// ============================================

import { Bot, InlineKeyboard } from 'grammy';
import { createClient } from '@supabase/supabase-js';
import 'dotenv/config';

// ============================================
// CONFIGURATION
// ============================================
const config = {
  BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN || '',
  SUPABASE_URL: process.env.SUPABASE_URL || '',
  SUPABASE_KEY: process.env.SUPABASE_ANON_KEY || '',
  OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
  WEBAPP_URL: process.env.WEBAPP_URL || 'https://t.me/hamyon_uz_bot/app',
};

const supabase = createClient(config.SUPABASE_URL, config.SUPABASE_KEY);
const bot = new Bot(config.BOT_TOKEN);

// ============================================
// 45+ CATEGORIES
// ============================================
const CATEGORIES = {
  expense: [
    { id: 'food', name: 'Oziq-ovqat', emoji: '🍕', keywords: ['food', 'grocery', 'oziq', 'ovqat', 'korzinka', 'makro', 'havas'] },
    { id: 'restaurants', name: 'Restoranlar', emoji: '🍽️', keywords: ['restaurant', 'restoran', 'lunch', 'tushlik', 'dinner', 'kechki', 'cafe', 'caravan', 'evos'] },
    { id: 'coffee', name: 'Kofe', emoji: '☕', keywords: ['coffee', 'kofe', 'tea', 'choy', 'starbucks', 'drink'] },
    { id: 'fastfood', name: 'Fast Food', emoji: '🍔', keywords: ['fastfood', 'burger', 'pizza', 'lavash', 'shaurma', 'mcdonalds', 'kfc'] },
    { id: 'delivery', name: 'Yetkazib berish', emoji: '🛵', keywords: ['delivery', 'yetkazib', 'express24', 'wolt', 'glovo'] },
    { id: 'taxi', name: 'Taksi', emoji: '🚕', keywords: ['taxi', 'taksi', 'yandex', 'uber', 'mytaxi', 'mashina'] },
    { id: 'fuel', name: 'Benzin', emoji: '⛽', keywords: ['fuel', 'benzin', 'gaz', 'yonilgi', 'zapravka'] },
    { id: 'publicTransport', name: 'Transport', emoji: '🚌', keywords: ['bus', 'avtobus', 'metro', 'transport'] },
    { id: 'parking', name: 'Parkovka', emoji: '🅿️', keywords: ['parking', 'parkovka', 'toxtash'] },
    { id: 'carMaintenance', name: 'Avto xizmat', emoji: '🔧', keywords: ['car', 'mashina', 'avto', 'remont', 'yog', 'service'] },
    { id: 'clothing', name: 'Kiyim', emoji: '👕', keywords: ['clothes', 'kiyim', 'koylak', 'shim', 'dress'] },
    { id: 'electronics', name: 'Elektronika', emoji: '📱', keywords: ['phone', 'telefon', 'laptop', 'kompyuter', 'texnika', 'mediapark'] },
    { id: 'accessories', name: 'Aksessuarlar', emoji: '👜', keywords: ['bag', 'sumka', 'wallet', 'hamyon', 'watch', 'soat'] },
    { id: 'gifts', name: 'Sovg\'alar', emoji: '🎁', keywords: ['gift', 'sovga', 'hadya', 'tuhfa', 'present'] },
    { id: 'beauty', name: 'Go\'zallik', emoji: '💄', keywords: ['beauty', 'cosmetics', 'kosmetika', 'salon', 'sartaroshxona'] },
    { id: 'rent', name: 'Ijara', emoji: '🏠', keywords: ['rent', 'ijara', 'kvartira', 'uy', 'apartment'] },
    { id: 'utilities', name: 'Kommunal', emoji: '💡', keywords: ['utilities', 'kommunal', 'elektr', 'tok', 'suv', 'gaz'] },
    { id: 'internet', name: 'Internet', emoji: '📶', keywords: ['internet', 'telefon', 'beeline', 'ucell', 'mobiuz', 'uzmobile'] },
    { id: 'furniture', name: 'Mebel', emoji: '🛋️', keywords: ['furniture', 'mebel', 'stol', 'stul', 'shkaf'] },
    { id: 'repairs', name: 'Ta\'mirlash', emoji: '🔨', keywords: ['repair', 'remont', 'tamir', 'qurilish'] },
    { id: 'movies', name: 'Kino', emoji: '🎬', keywords: ['movie', 'kino', 'film', 'cinema', 'imax'] },
    { id: 'games', name: 'O\'yinlar', emoji: '🎮', keywords: ['game', 'oyin', 'playstation', 'xbox', 'steam'] },
    { id: 'subscriptions', name: 'Obunalar', emoji: '📺', keywords: ['subscription', 'obuna', 'netflix', 'spotify', 'youtube', 'premium'] },
    { id: 'concerts', name: 'Konsertlar', emoji: '🎵', keywords: ['concert', 'konsert', 'festival', 'event', 'tadbir'] },
    { id: 'hobbies', name: 'Sevimli mashg\'ulot', emoji: '🎨', keywords: ['hobby', 'sevimli', 'art', 'craft'] },
    { id: 'pharmacy', name: 'Dorixona', emoji: '💊', keywords: ['pharmacy', 'dorixona', 'dori', 'apteka', 'medicine', 'tabletka'] },
    { id: 'doctor', name: 'Shifokor', emoji: '🏥', keywords: ['doctor', 'shifokor', 'vrach', 'hospital', 'kasalxona', 'clinic', 'klinika'] },
    { id: 'gym', name: 'Sport zal', emoji: '💪', keywords: ['gym', 'zal', 'fitness', 'fitnes', 'trenirovka', 'workout'] },
    { id: 'sports', name: 'Sport', emoji: '⚽', keywords: ['sport', 'futbol', 'football', 'tennis', 'suzish'] },
    { id: 'wellness', name: 'Sog\'lomlik', emoji: '🧘', keywords: ['spa', 'massage', 'massaj', 'sauna', 'hammom'] },
    { id: 'courses', name: 'Kurslar', emoji: '📚', keywords: ['course', 'kurs', 'lesson', 'dars', 'talim', 'education'] },
    { id: 'books', name: 'Kitoblar', emoji: '📖', keywords: ['book', 'kitob', 'oqish', 'reading'] },
    { id: 'tuition', name: 'O\'qish to\'lovi', emoji: '🎓', keywords: ['tuition', 'maktab', 'universitet', 'school', 'tolov'] },
    { id: 'supplies', name: 'O\'quv anjomlari', emoji: '✏️', keywords: ['supplies', 'daftar', 'ruchka', 'stationery'] },
    { id: 'flights', name: 'Parvozlar', emoji: '✈️', keywords: ['flight', 'parvoz', 'samolyot', 'bilet', 'avia', 'uzbekistan airways'] },
    { id: 'hotels', name: 'Mehmonxona', emoji: '🏨', keywords: ['hotel', 'mehmonxona', 'booking', 'yashash'] },
    { id: 'vacation', name: 'Dam olish', emoji: '🏖️', keywords: ['vacation', 'dam olish', 'sayohat', 'travel', 'trip'] },
    { id: 'businessTravel', name: 'Xizmat safari', emoji: '💼', keywords: ['business trip', 'komandirovka', 'xizmat safari'] },
    { id: 'pets', name: 'Uy hayvonlari', emoji: '🐕', keywords: ['pet', 'hayvon', 'it', 'mushuk', 'dog', 'cat', 'vet'] },
    { id: 'charity', name: 'Xayriya', emoji: '❤️', keywords: ['charity', 'xayriya', 'sadaqa', 'yordam', 'donation'] },
    { id: 'insurance', name: 'Sug\'urta', emoji: '🛡️', keywords: ['insurance', 'sugurta'] },
    { id: 'taxes', name: 'Soliqlar', emoji: '📋', keywords: ['tax', 'soliq', 'nalog'] },
    { id: 'childcare', name: 'Bolalar', emoji: '👶', keywords: ['baby', 'bola', 'child', 'kids', 'bogcha', 'daycare'] },
    { id: 'other', name: 'Boshqa', emoji: '📦', keywords: ['other', 'boshqa', 'turli'] },
  ],
  income: [
    { id: 'salary', name: 'Oylik maosh', emoji: '💰', keywords: ['salary', 'oylik', 'maosh', 'ish haqi', 'wage', 'pay'] },
    { id: 'freelance', name: 'Frilanser', emoji: '💻', keywords: ['freelance', 'frilanser', 'project', 'loyiha'] },
    { id: 'business', name: 'Biznes', emoji: '🏢', keywords: ['business', 'biznes', 'profit', 'foyda', 'tushum'] },
    { id: 'investments', name: 'Investitsiya', emoji: '📈', keywords: ['investment', 'investitsiya', 'dividend', 'aksiya'] },
    { id: 'rental', name: 'Ijara daromadi', emoji: '🏘️', keywords: ['rental income', 'ijara daromadi', 'ijaraga'] },
    { id: 'gifts_income', name: 'Sovg\'a olindi', emoji: '🎀', keywords: ['gift received', 'sovga oldim', 'hadya'] },
    { id: 'refunds', name: 'Qaytarilgan pul', emoji: '↩️', keywords: ['refund', 'return', 'qaytarish', 'vozvrat'] },
    { id: 'bonus', name: 'Bonus', emoji: '🎉', keywords: ['bonus', 'premiya', 'mukofot'] },
    { id: 'cashback', name: 'Keshbek', emoji: '💳', keywords: ['cashback', 'keshbek', 'qaytim'] },
    { id: 'other_income', name: 'Boshqa daromad', emoji: '💵', keywords: ['income', 'daromad', 'pul keldi', 'tushdi', 'oldim'] },
  ],
};

// ============================================
// DATABASE HELPERS
// ============================================
async function getOrCreateUser(telegramId: number, firstName: string, lastName?: string) {
  const { data: existing } = await supabase
    .from('users')
    .select('*')
    .eq('telegram_id', telegramId)
    .single();

  if (existing) return existing;

  const { data: newUser } = await supabase
    .from('users')
    .insert({
      telegram_id: telegramId,
      name: `${firstName}${lastName ? ' ' + lastName : ''}`,
      balance: 0,
      created_at: new Date().toISOString(),
    })
    .select()
    .single();

  return newUser;
}

async function saveTransaction(telegramId: number, tx: { description: string; amount: number; categoryId: string; source: string }) {
  const { data } = await supabase
    .from('transactions')
    .insert({
      user_telegram_id: telegramId,
      description: tx.description,
      amount: tx.amount,
      category_id: tx.categoryId,
      source: tx.source,
      created_at: new Date().toISOString(),
    })
    .select()
    .single();

  await supabase.rpc('update_balance', { p_telegram_id: telegramId, p_amount: tx.amount });
  return data;
}

async function getBalance(telegramId: number): Promise<number> {
  const { data } = await supabase.from('users').select('balance').eq('telegram_id', telegramId).single();
  return data?.balance || 0;
}

async function getTodayStats(telegramId: number) {
  const today = new Date().toISOString().split('T')[0];
  const { data } = await supabase.from('transactions').select('amount').eq('user_telegram_id', telegramId).gte('created_at', today);
  let expenses = 0, income = 0;
  if (data) {
    data.forEach((tx) => { 
      if (tx.amount < 0) expenses += Math.abs(tx.amount); 
      else income += tx.amount; 
    });
  }
  return { expenses, income, count: data?.length || 0 };
}

// ============================================
// PARSING HELPERS
// ============================================
function parseAmount(text: string): number | null {
  const lower = text.toLowerCase();
  const millionMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(?:m|mln|million|миллион|млн)/i);
  if (millionMatch) return parseFloat(millionMatch[1].replace(',', '.')) * 1000000;
  const kMatch = lower.match(/(\d+(?:[.,]\d+)?)\s*(?:k|к|тысяч|ming|минг)/i);
  if (kMatch) return parseFloat(kMatch[1].replace(',', '.')) * 1000;
  const formattedMatch = text.match(/(\d{1,3}(?:[,\s]\d{3})+)/);
  if (formattedMatch) return parseInt(formattedMatch[1].replace(/[,\s]/g, ''));
  const simpleMatch = text.match(/(\d+)/);
  if (simpleMatch && parseInt(simpleMatch[1]) >= 100) return parseInt(simpleMatch[1]);
  return null;
}

interface Category {
  id: string;
  name: string;
  emoji: string;
  keywords: string[];
}

function detectCategory(text: string): { id: string; type: 'expense' | 'income'; category: Category } {
  const lower = text.toLowerCase();
  for (const cat of CATEGORIES.income) {
    for (const kw of cat.keywords) { if (lower.includes(kw)) return { id: cat.id, type: 'income', category: cat }; }
  }
  for (const cat of CATEGORIES.expense) {
    for (const kw of cat.keywords) { if (lower.includes(kw)) return { id: cat.id, type: 'expense', category: cat }; }
  }
  const defaultCat = CATEGORIES.expense.find(c => c.id === 'other')!;
  return { id: 'other', type: 'expense', category: defaultCat };
}

function getCategoryById(id: string): Category {
  const all = [...CATEGORIES.expense, ...CATEGORIES.income];
  return all.find(c => c.id === id) || { id: 'other', name: 'Boshqa', emoji: '📦', keywords: [] };
}

function formatMoney(amount: number): string {
  const abs = Math.abs(amount);
  if (abs >= 1000000) return (amount / 1000000).toFixed(1).replace('.0', '') + 'M UZS';
  return amount.toLocaleString('en-US').replace(/,/g, ' ') + ' UZS';
}

// ============================================
// VOICE TRANSCRIPTION (OpenAI Whisper)
// ============================================
async function transcribeVoice(fileUrl: string): Promise<string> {
  try {
    const audioResponse = await fetch(fileUrl);
    const audioBuffer = await audioResponse.arrayBuffer();
    const formData = new FormData();
    formData.append('file', new Blob([audioBuffer], { type: 'audio/ogg' }), 'voice.ogg');
    formData.append('model', 'whisper-1');
    formData.append('language', 'uz');
    const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST', 
      headers: { 'Authorization': `Bearer ${config.OPENAI_API_KEY}` }, 
      body: formData,
    });
    const result = await response.json();
    return result.text || '';
  } catch (error) { 
    console.error('Whisper error:', error); 
    return ''; 
  }
}

// ============================================
// RECEIPT OCR (GPT-4 Vision)
// ============================================
async function extractReceiptData(imageUrl: string): Promise<{ amount: number; store: string } | null> {
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${config.OPENAI_API_KEY}`, 
        'Content-Type': 'application/json' 
      },
      body: JSON.stringify({
        model: 'gpt-4o',
        messages: [{ 
          role: 'user', 
          content: [
            { type: 'text', text: `Chekdan umumiy summa va do'kon nomini ajrating. JSON: {"amount": number, "store": "string"}` },
            { type: 'image_url', image_url: { url: imageUrl } },
          ]
        }],
        max_tokens: 150,
      }),
    });
    const result = await response.json();
    const content = result.choices?.[0]?.message?.content || '';
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      if (!parsed.error && parsed.amount) return { amount: parsed.amount, store: parsed.store || 'Chek' };
    }
    return null;
  } catch (error) { 
    console.error('Vision error:', error); 
    return null; 
  }
}

// ============================================
// BOT COMMANDS
// ============================================
bot.command('start', async (ctx) => {
  const from = ctx.from;
  if (!from) return;
  
  await getOrCreateUser(from.id, from.first_name, from.last_name);
  const keyboard = new InlineKeyboard().webApp('📊 Hamyon ilovasini ochish', config.WEBAPP_URL);
  
  await ctx.reply(
    `👋 Salom! Men Hamyon - moliyaviy yordamchingizman.\n\n` +
    `📱 *Tranzaksiya qo'shish usullari:*\n\n` +
    `🎤 *Ovozli xabar* - "Kofe 15 ming", "Taksi 30k"\n` +
    `💬 *Matn* - "Tushlik 45000"\n` +
    `📷 *Chek* - Chek rasmini yuboring\n\n` +
    `Barcha funksiyalar BEPUL! 🚀`,
    { parse_mode: 'Markdown', reply_markup: keyboard }
  );
});

bot.command('balance', async (ctx) => {
  const from = ctx.from;
  if (!from) return;
  
  const balance = await getBalance(from.id);
  const today = await getTodayStats(from.id);
  const keyboard = new InlineKeyboard().webApp('📊 To\'liq ilova', config.WEBAPP_URL);
  
  await ctx.reply(
    `💰 *Balans: ${formatMoney(balance)}*\n\n📅 Bugun:\n↘️ Xarajat: ${formatMoney(today.expenses)}\n↗️ Daromad: ${formatMoney(today.income)}`,
    { parse_mode: 'Markdown', reply_markup: keyboard }
  );
});

bot.command('help', async (ctx) => {
  await ctx.reply(
    `🎙️ *Ovozli xabar:*\n1. Mikrofon tugmasini bosib turing\n2. "Kofe 15 ming" deb ayting\n3. Yuborish uchun qo'yib yuboring\n\n` +
    `💬 *Matn:* "Taksi 30000" deb yozing\n\n📷 *Chek:* Rasm yuboring`,
    { parse_mode: 'Markdown' }
  );
});

// ============================================
// VOICE MESSAGE HANDLER
// ============================================
bot.on('message:voice', async (ctx) => {
  const from = ctx.from;
  const voice = ctx.message?.voice;
  
  if (!from || !voice) return;
  
  await ctx.reply('🎤 Qayta ishlanmoqda...');
  
  try {
    const file = await ctx.api.getFile(voice.file_id);
    const fileUrl = `https://api.telegram.org/file/bot${config.BOT_TOKEN}/${file.file_path}`;
    const transcription = await transcribeVoice(fileUrl);
    
    if (!transcription) { 
      await ctx.reply('❌ Tushunib bo\'lmadi. Qayta urinib ko\'ring.'); 
      return; 
    }
    
    const amount = parseAmount(transcription);
    const { id: categoryId, type, category } = detectCategory(transcription);
    
    if (!amount) { 
      await ctx.reply(`📝 Eshitdim: "${transcription}"\n\n❌ Summani aniqlab bo\'lmadi.`); 
      return; 
    }
    
    const finalAmount = type === 'expense' ? -Math.abs(amount) : Math.abs(amount);
    await saveTransaction(from.id, { description: transcription, amount: finalAmount, categoryId, source: 'voice' });
    const balance = await getBalance(from.id);
    const keyboard = new InlineKeyboard().webApp('📊 Ilovani ochish', config.WEBAPP_URL);
    
    await ctx.reply(
      `✅ *Saqlandi!*\n\n${category.emoji} ${category.name}\n💸 ${formatMoney(Math.abs(finalAmount))}\n💰 Balans: ${formatMoney(balance)}`,
      { parse_mode: 'Markdown', reply_markup: keyboard }
    );
  } catch (error) { 
    console.error('Voice error:', error); 
    await ctx.reply('❌ Xatolik yuz berdi.'); 
  }
});

// ============================================
// PHOTO HANDLER
// ============================================
bot.on('message:photo', async (ctx) => {
  const from = ctx.from;
  const photo = ctx.message?.photo;
  
  if (!from || !photo || photo.length === 0) return;
  
  await ctx.reply('📷 Skanerlanmoqda...');
  
  try {
    const file = await ctx.api.getFile(photo[photo.length - 1].file_id);
    const fileUrl = `https://api.telegram.org/file/bot${config.BOT_TOKEN}/${file.file_path}`;
    const receiptData = await extractReceiptData(fileUrl);
    
    if (!receiptData) { 
      await ctx.reply('❌ Chekni o\'qib bo\'lmadi.'); 
      return; 
    }
    
    const { id: categoryId, category } = detectCategory(receiptData.store);
    await saveTransaction(from.id, { description: receiptData.store, amount: -Math.abs(receiptData.amount), categoryId, source: 'receipt' });
    const balance = await getBalance(from.id);
    const keyboard = new InlineKeyboard().webApp('📊 Ilovani ochish', config.WEBAPP_URL);
    
    await ctx.reply(
      `✅ *Chek qabul qilindi!*\n\n🏪 ${receiptData.store}\n💸 ${formatMoney(receiptData.amount)}\n${category.emoji} ${category.name}\n💰 Balans: ${formatMoney(balance)}`,
      { parse_mode: 'Markdown', reply_markup: keyboard }
    );
  } catch (error) { 
    console.error('Photo error:', error); 
    await ctx.reply('❌ Xatolik yuz berdi.'); 
  }
});

// ============================================
// TEXT HANDLER
// ============================================
bot.on('message:text', async (ctx) => {
  const from = ctx.from;
  const text = ctx.message?.text;
  
  if (!from || !text) return;
  if (text.startsWith('/')) return;
  
  const amount = parseAmount(text);
  const { id: categoryId, type, category } = detectCategory(text);
  
  if (!amount) { 
    await ctx.reply('❌ Summani aniqlab bo\'lmadi.\n\n💡 Masalan: "Kofe 15000"'); 
    return; 
  }
  
  const finalAmount = type === 'expense' ? -Math.abs(amount) : Math.abs(amount);
  await saveTransaction(from.id, { description: text, amount: finalAmount, categoryId, source: 'text' });
  const balance = await getBalance(from.id);
  const keyboard = new InlineKeyboard().webApp('📊 Ilovani ochish', config.WEBAPP_URL);
  
  await ctx.reply(
    `✅ *Saqlandi!*\n\n${category.emoji} ${category.name}\n${type === 'expense' ? '💸' : '💰'} ${formatMoney(Math.abs(finalAmount))}\n💰 Balans: ${formatMoney(balance)}`,
    { parse_mode: 'Markdown', reply_markup: keyboard }
  );
});

// ============================================
// CALLBACK HANDLERS
// ============================================
bot.callbackQuery('view_balance', async (ctx) => {
  const from = ctx.from;
  if (!from) return;
  
  const balance = await getBalance(from.id);
  const today = await getTodayStats(from.id);
  
  await ctx.answerCallbackQuery();
  await ctx.reply(
    `💰 *Balans: ${formatMoney(balance)}*\n\n📅 Bugun:\n↘️ Xarajat: ${formatMoney(today.expenses)}\n↗️ Daromad: ${formatMoney(today.income)}`,
    { parse_mode: 'Markdown' }
  );
});

// ============================================
// START BOT
// ============================================
bot.catch((err) => console.error('Bot error:', err));
console.log('🚀 Hamyon Bot ishga tushdi...');
bot.start();
