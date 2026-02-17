import asyncio
from datetime import datetime
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import config
from database import get_db, User, Payment
from crypto_payments import crypto_pay

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def get_main_menu_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить Telegram Stars", callback_data="buy_stars_menu")
    builder.button(text="💰 Мои покупки", callback_data="my_purchases")
    builder.button(text="👑 Топ покупателей", callback_data="top_buyers")
    builder.button(text="💬 Поддержка", url="https://t.me/star_support")
    builder.adjust(1)
    return builder

def get_star_packages_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    
    for stars, price in config.STAR_PRICES.items():
        builder.button(
            text=f"⭐ {stars} stars - {price}₽",
            callback_data=f"buy_stars:{stars}"
        )
    
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(2)
    return builder

def get_payment_method_keyboard(stars: int, price: float) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    
    builder.button(text="💳 Оплатить USDT (Crypto Bot)", callback_data=f"pay_crypto:{stars}:{price}")
    builder.button(text="◀️ Назад", callback_data=f"buy_stars:{stars}")
    builder.adjust(1)
    return builder

def get_crypto_payment_keyboard(invoice_data: dict, stars: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    
    if invoice_data.get("bot_invoice_url"):
        builder.button(text="📱 Оплатить в Telegram", url=invoice_data["bot_invoice_url"])
    
    if invoice_data.get("web_app_invoice_url"):
        builder.button(text="🌐 Оплатить в браузере", url=invoice_data["web_app_invoice_url"])
    
    builder.button(text="🔄 Проверить статус", callback_data=f"check_crypto:{invoice_data['invoice_id']}:{invoice_data['payment_id']}")
    builder.button(text="◀️ Назад", callback_data=f"buy_stars:{stars}")
    builder.adjust(1)
    return builder

def get_admin_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🔙 В меню", callback_data="main_menu")
    builder.adjust(1)
    return builder

async def send_main_menu(user_id: int, message_to_delete: Message = None):
    db: Session = next(get_db())
    
    user = db.query(User).filter(User.telegram_id == user_id).first()
    
    if not user:
        user = User(
            telegram_id=user_id,
            username="",
            full_name="",
            is_admin=user_id in config.ADMIN_IDS
        )
        db.add(user)
        db.commit()
    
    total_purchases = db.query(func.sum(Payment.amount)).filter(
        Payment.user_id == user_id,
        Payment.status == "completed"
    ).scalar() or 0
    
    total_stars = db.query(func.sum(Payment.stars_amount)).filter(
        Payment.user_id == user_id,
        Payment.status == "completed"
    ).scalar() or 0
    
    caption = f"""
🌟 <b>Добро пожаловать в Kondr Shop!</b> 🌟

Здесь вы можете купить <b>Telegram Stars</b> по выгодной цене!

🚀 <b>Почему у нас выгодно?</b>
• Цены ниже официальных
• Моментальная доставка
• Безопасные платежи (USDT)

📊 <b>Ваша статистика:</b>
💰 Всего потрачено: {total_purchases:.0f}₽
⭐ Всего куплено: {total_stars} stars

<i>Выберите действие:</i>
    """
    
    if message_to_delete:
        try:
            await message_to_delete.delete()
        except:
            pass
    
    try:
        await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile("assets/welcome.jpg") if os.path.exists("assets/welcome.jpg") else "https://via.placeholder.com/600x300/2E2B5F/FFFFFF?text=Telegram+Stars+Store",
            caption=caption,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard().as_markup()
        )
    except Exception as e:
        print(f"Ошибка отправки фото: {e}")
        await bot.send_message(
            chat_id=user_id,
            text=caption,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard().as_markup()
        )

@dp.message(Command("start"))
async def cmd_start(message: Message):
    db: Session = next(get_db())
    
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            is_admin=message.from_user.id in config.ADMIN_IDS
        )
        db.add(user)
        db.commit()
    
    await send_main_menu(message.from_user.id)

@dp.callback_query(F.data == "buy_stars_menu")
async def show_star_packages(callback: CallbackQuery):
    text = """
✨ <b>Выберите пакет Telegram Stars:</b> ✨
    """
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_star_packages_keyboard().as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "my_purchases")
async def show_purchases(callback: CallbackQuery):
    db: Session = next(get_db())
    
    payments = db.query(Payment).filter(
        Payment.user_id == callback.from_user.id,
        Payment.status.in_(["paid", "completed"])
    ).order_by(Payment.paid_at.desc()).limit(10).all()
    
    if not payments:
        text = "📭 <b>У вас еще нет покупок.</b>"
    else:
        text = "🛒 <b>Ваши последние покупки:</b>\n\n"
        
        for i, payment in enumerate(payments, 1):
            method = "USDT" if payment.payment_method == "crypto" else "RUB"
            status_icon = "✅" if payment.status == "completed" else "⏳"
            text += f"{i}. ⭐ {payment.stars_amount} stars - {payment.amount}₽\n"
            text += f"   💳 {method} | {status_icon} {payment.status}\n"
            text += f"   📅 {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить ещё", callback_data="buy_stars_menu")
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_stars:"))
async def process_star_package(callback: CallbackQuery):
    stars = int(callback.data.split(":")[1])
    price = config.STAR_PRICES[stars]
    
    usdt_amount = price / 95
    
    text = f"""
🎯 <b>Подтверждение заказа</b>

📦 <b>Пакет:</b> ⭐ {stars} Telegram Stars
💰 <b>Цена:</b> {price}₽ (~{usdt_amount:.2f} USDT)

💳 <b>Способ оплаты:</b> USDT (Crypto Bot)

✅ <i>Нажмите кнопку ниже для создания счёта</i>
    """
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_payment_method_keyboard(stars, price).as_markup()
        )
    except:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_payment_method_keyboard(stars, price).as_markup()
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_crypto:"))
async def pay_with_crypto(callback: CallbackQuery):
    _, stars_str, price_str = callback.data.split(":")
    stars = int(stars_str)
    price = float(price_str)
    
    db: Session = next(get_db())
    
    payment_id = f"crypto_{callback.from_user.id}_{int(datetime.now().timestamp())}"
    
    payment = Payment(
        user_id=callback.from_user.id,
        payment_id=payment_id,
        amount=price,
        stars_amount=stars,
        status="pending",
        payment_method="crypto",
        created_at=datetime.utcnow()
    )
    db.add(payment)
    
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    if user:
        user.total_spent += price
    
    db.commit()
    
    invoice = await crypto_pay.create_usdt_invoice(
        amount_rub=price,
        description=f"Покупка {stars} Telegram Stars",
        payload=payment_id
    )
    
    if invoice:
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if payment:
            payment.payment_id = f"crypto_invoice_{invoice['invoice_id']}"
            db.commit()
        
        invoice_data = {
            **invoice,
            "payment_id": f"crypto_invoice_{invoice['invoice_id']}",
            "invoice_id": invoice['invoice_id']
        }
        
        text = f"""
✅ <b>Счёт USDT создан!</b>

📦 <b>Пакет:</b> ⭐ {stars} Telegram Stars
💰 <b>К оплате:</b> {price}₽ (~{invoice['usdt_amount']:.2f} USDT)
💱 <b>Курс:</b> 1 USDT ≈ {invoice['rate']:.2f}₽
🆔 <b>ID:</b> <code>{invoice_data['payment_id']}</code>
⏰ <b>Действителен:</b> 30 минут

💳 <b>Для оплаты нажмите кнопку ниже:</b>
        """
        
        try:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=get_crypto_payment_keyboard(invoice_data, stars).as_markup()
            )
        except:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=get_crypto_payment_keyboard(invoice_data, stars).as_markup()
            )
    else:
        await callback.answer(
            "❌ Ошибка при создании счёта. Попробуйте позже или обратитесь в поддержку.",
            show_alert=True
        )

@dp.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto_payment(callback: CallbackQuery):
    _, invoice_id_str, payment_id = callback.data.split(":")
    invoice_id = int(invoice_id_str)
    
    paid = await crypto_pay.check_invoice_paid(invoice_id)
    
    if paid:
        db: Session = next(get_db())
        
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        if payment:
            payment.status = "paid"
            payment.paid_at = datetime.utcnow()
            db.commit()
        
        text = f"""
🎉 <b>Оплата подтверждена!</b>

✅ <b>Ваш заказ обрабатывается</b>
💰 <b>Сумма:</b> {payment.amount}₽

✨ <b>Звёзды будут отправлены на ваш аккаунт в течение 5 минут!</b>

📞 <i>Если возникнут вопросы, обратитесь в поддержку: @star_support</i>
        """
        
        builder = InlineKeyboardBuilder()
        builder.button(text="⭐ Купить ещё", callback_data="buy_stars_menu")
        builder.button(text="◀️ В меню", callback_data="main_menu")
        builder.adjust(1)
        
        try:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
        except:
            await callback.message.answer(
                text,
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
    else:
        await callback.answer(
            "⏳ Оплата еще не поступила. Попробуйте позже или проверьте статус в Crypto Bot.",
            show_alert=True
        )

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await send_main_menu(callback.from_user.id, callback.message)
    await callback.answer()

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    
    text = """
👑 <b>Админ панель Stars Store</b>

<b>Доступные действия:</b>
• 📊 Статистика продаж
    """
    
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_keyboard().as_markup()
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    db: Session = next(get_db())
    
    total_users = db.query(User).count()
    total_orders = db.query(Payment).count()
    completed_orders = db.query(Payment).filter(Payment.status == "completed").count()
    pending_orders = db.query(Payment).filter(Payment.status == "pending").count()
    crypto_orders = db.query(Payment).filter(Payment.payment_method == "crypto").count()
    
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status.in_(["paid", "completed"])
    ).scalar() or 0
    
    total_stars = db.query(func.sum(Payment.stars_amount)).filter(
        Payment.status == "completed"
    ).scalar() or 0
    
    text = f"""
📊 <b>Статистика магазина</b>

👥 <b>Всего пользователей:</b> {total_users}
📦 <b>Всего заказов:</b> {total_orders}
✅ <b>Выполнено:</b> {completed_orders}
⏳ <b>Ожидает:</b> {pending_orders}

💰 <b>Общая выручка:</b> {total_revenue:.2f}₽
⭐ <b>Отправлено stars:</b> {total_stars}

💳 <b>Способ оплаты:</b>
• USDT (Crypto Bot): {crypto_orders} заказов

🕒 <b>Обновлено:</b> {datetime.now().strftime('%H:%M:%S')}
    """
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_admin_keyboard().as_markup()
        )
    except:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_admin_keyboard().as_markup()
        )
    await callback.answer()

@dp.callback_query(F.data == "top_buyers")
async def show_top_buyers(callback: CallbackQuery):
    db: Session = next(get_db())
    
    top_buyers = db.query(
        User.username, 
        User.full_name,
        func.sum(Payment.amount).label('total_spent'),
        func.sum(Payment.stars_amount).label('total_stars')
    ).join(Payment, User.telegram_id == Payment.user_id).filter(
        Payment.status == "completed"
    ).group_by(User.id).order_by(
        func.sum(Payment.amount).desc()
    ).limit(10).all()
    
    if not top_buyers:
        text = "📊 <b>Пока нет данных о покупках.</b>"
    else:
        text = "👑 <b>Топ покупателей:</b>\n\n"
        
        for i, (username, full_name, total_spent, total_stars) in enumerate(top_buyers, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "🏅"))
            name = f"@{username}" if username else full_name or f"Покупатель {i}"
            text += f"{medal} {i}. {name}\n"
            text += f"   💰 {total_spent:.0f}₽ | ⭐ {total_stars} stars\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить звёзды", callback_data="buy_stars_menu")
    builder.button(text="◀️ В меню", callback_data="main_menu")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    await callback.answer()

async def main():
    print("🤖 Kondr Shop (Telegram Stars) запущен!")
    print(f"👑 Администраторы: {config.ADMIN_IDS}")
    print(f"💎 Цены: {config.STAR_PRICES}")
    
    if config.CRYPTO_PAY_TOKEN:
        print(f"💳 Доступна оплата: USDT (Crypto Bot)")
        if config.CRYPTO_PAY_TESTNET:
            print(f"⚠️ Crypto Bot работает в тестовом режиме (testnet)")
    else:
        print("⚠️ ВНИМАНИЕ: Не настроен Crypto Bot!")
    
    print(f"💬 Поддержка: @star_support")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())