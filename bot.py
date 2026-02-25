import os
import asyncio
from dataclasses import dataclass
from typing import Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8742351117:AAGoizZ2vuK7x7-VMRpOI2slWQL_x9DAepg", "")
ADMIN_IDS = set(int(x) for x in (os.getenv("7958070473", "") or "").split(",") if x.strip())

# ===== DEMO DATA (DB o‘rniga) =====
@dataclass
class Product:
    id: int
    category: str
    name: str
    price: int

CATEGORIES = ["Telefon", "Aksesuar", "Noutbuk"]

PRODUCTS: List[Product] = [
    Product(1, "Telefon", "iPhone 13", 8500000),
    Product(2, "Telefon", "Samsung A54", 4200000),
    Product(3, "Aksesuar", "AirPods", 1500000),
    Product(4, "Noutbuk", "Lenovo ThinkPad", 7800000),
]

# user_id -> {product_id: qty}
CART: Dict[int, Dict[int, int]] = {}

def kb_categories():
    rows = []
    for c in CATEGORIES:
        rows.append([InlineKeyboardButton(text=c, callback_data=f"cat:{c}")])
    rows.append([InlineKeyboardButton(text="🛒 Savat", callback_data="cart:show")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_products(category: str):
    rows = []
    for p in PRODUCTS:
        if p.category == category:
            rows.append([InlineKeyboardButton(
                text=f"{p.name} — {p.price:,} so'm",
                callback_data=f"prod:{p.id}"
            )])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="home")])
    rows.append([InlineKeyboardButton(text="🛒 Savat", callback_data="cart:show")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_product_actions(product_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Savatga qo‘shish", callback_data=f"cart:add:{product_id}"),
        ],
        [
            InlineKeyboardButton(text="🛒 Savat", callback_data="cart:show"),
            InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="home"),
        ]
    ])

def kb_cart_actions():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="order:start")],
        [InlineKeyboardButton(text="🧹 Savatni tozalash", callback_data="cart:clear")],
        [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="home")],
    ])

def cart_total(user_id: int) -> int:
    total = 0
    for pid, qty in CART.get(user_id, {}).items():
        p = next((x for x in PRODUCTS if x.id == pid), None)
        if p:
            total += p.price * qty
    return total

def cart_text(user_id: int) -> str:
    items = CART.get(user_id, {})
    if not items:
        return "🛒 Savatingiz bo‘sh."
    lines = ["🛒 Savat:"]
    for pid, qty in items.items():
        p = next((x for x in PRODUCTS if x.id == pid), None)
        if p:
            lines.append(f"- {p.name} x{qty} = {(p.price*qty):,} so'm")
    lines.append(f"\nJami: {cart_total(user_id):,} so'm")
    return "\n".join(lines)

def contact_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

async def main():
    if not BOT_TOKEN or "PASTE_NEW_TOKEN_HERE" in BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env ga qo‘yilmagan yoki noto‘g‘ri.")

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    # ===== START =====
    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            "Assalomu alaykum! 🛍\nKategoriyadan mahsulot tanlang:",
            reply_markup=kb_categories()
        )

    # ===== HOME =====
    @dp.callback_query(F.data == "home")
    async def home(c: CallbackQuery):
        await c.message.edit_text("Kategoriyadan tanlang:", reply_markup=kb_categories())
        await c.answer()

    # ===== CATEGORY -> PRODUCTS =====
    @dp.callback_query(F.data.startswith("cat:"))
    async def open_category(c: CallbackQuery):
        category = c.data.split(":", 1)[1]
        await c.message.edit_text(f"📦 {category} — mahsulotlar:", reply_markup=kb_products(category))
        await c.answer()

    # ===== PRODUCT DETAILS =====
    @dp.callback_query(F.data.startswith("prod:"))
    async def open_product(c: CallbackQuery):
        pid = int(c.data.split(":", 1)[1])
        p = next((x for x in PRODUCTS if x.id == pid), None)
        if not p:
            await c.answer("Mahsulot topilmadi", show_alert=True)
            return
        await c.message.edit_text(
            f"🛒 {p.name}\nNarx: {p.price:,} so'm\n\nSavatga qo‘shasizmi?",
            reply_markup=kb_product_actions(pid)
        )
        await c.answer()

    # ===== CART ADD =====
    @dp.callback_query(F.data.startswith("cart:add:"))
    async def cart_add(c: CallbackQuery):
        pid = int(c.data.split(":")[2])
        CART.setdefault(c.from_user.id, {})
        CART[c.from_user.id][pid] = CART[c.from_user.id].get(pid, 0) + 1
        await c.answer("✅ Savatga qo‘shildi")
        # xohlasangiz cartni ham ko‘rsatib yuboramiz:
        await c.message.edit_text(cart_text(c.from_user.id), reply_markup=kb_cart_actions())

    # ===== CART SHOW =====
    @dp.callback_query(F.data == "cart:show")
    async def cart_show(c: CallbackQuery):
        await c.message.edit_text(cart_text(c.from_user.id), reply_markup=kb_cart_actions())
        await c.answer()

    # ===== CART CLEAR =====
    @dp.callback_query(F.data == "cart:clear")
    async def cart_clear(c: CallbackQuery):
        CART[c.from_user.id] = {}
        await c.message.edit_text("🧹 Savat tozalandi.\nKategoriyani tanlang:", reply_markup=kb_categories())
        await c.answer()

    # ===== ORDER START -> CONTACT =====
    @dp.callback_query(F.data == "order:start")
    async def order_start(c: CallbackQuery):
        if not CART.get(c.from_user.id):
            await c.answer("Savat bo‘sh.", show_alert=True)
            return
        await c.message.answer("📞 Telefon raqamingizni yuboring:", reply_markup=contact_kb())
        await c.answer()

    # ===== RECEIVE CONTACT =====
    @dp.message(F.contact)
    async def got_contact(m: Message):
        m.bot_data["phone_"+str(m.from_user.id)] = m.contact.phone_number
        await m.answer("📍 Manzilingizni yozing (masalan: Chilonzor, 5-mavze, 12-uy):", reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True
        ))

    # ===== RECEIVE ADDRESS =====
    @dp.message(F.text)
    async def got_text(m: Message):
        if m.text == "❌ Bekor qilish":
            await m.answer("Bekor qilindi. Kategoriyani tanlang:", reply_markup=kb_categories())
            return

        key = "phone_"+str(m.from_user.id)
        if key in m.bot_data and CART.get(m.from_user.id):
            phone = m.bot_data.pop(key)
            address = m.text.strip()
            total = cart_total(m.from_user.id)

            order_summary = (
                "✅ Buyurtma qabul qilindi!\n\n"
                f"{cart_text(m.from_user.id)}\n\n"
                f"📞 Telefon: {phone}\n"
                f"📍 Manzil: {address}\n"
                f"👤 Mijoz: @{m.from_user.username or 'username yo‘q'} (ID: {m.from_user.id})"
            )

            # Adminlarga yuborish
            for admin_id in ADMIN_IDS:
                try:
                    await m.bot.send_message(admin_id, "🆕 Yangi buyurtma!\n\n" + order_summary)
                except Exception:
                    pass

            # Mijozga tasdiq
            CART[m.from_user.id] = {}
            await m.answer(order_summary + "\n\nTez orada operator bog‘lanadi.", reply_markup=kb_categories())
        else:
            # oddiy chat yozsa — yo‘naltiramiz
            await m.answer("Kategoriyadan mahsulot tanlang:", reply_markup=kb_categories())

    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())