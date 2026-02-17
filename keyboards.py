from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from config import config

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⭐ Купить звёзды")],
            [KeyboardButton(text="💰 Мой баланс"), KeyboardButton(text="🎁 История покупок")],
            [KeyboardButton(text="👑 Топ покупателей"), KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

def get_star_packages_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    row = []
    for stars, price in config.STAR_PRICES.items():
        if len(row) == 2:
            keyboard.inline_keyboard.append(row)
            row = []
        row.append(
            InlineKeyboardButton(
                text=f"⭐ {stars} звёзд - {price}₽",
                callback_data=f"buy_stars:{stars}"
            )
        )
    
    if row:
        keyboard.inline_keyboard.append(row)
    
    keyboard.inline_keyboard.extend([
        [
            InlineKeyboardButton(
                text="💳 Другой вариант",
                callback_data="custom_amount"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="main_menu"
            )
        ]
    ])
    
    return keyboard

def get_payment_confirmation_keyboard(stars: int, price: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить покупку",
                    callback_data=f"confirm_purchase:{stars}:{price}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить количество",
                    callback_data="change_amount"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_purchase"
                )
            ]
        ]
    )

def get_payment_method_keyboard(payment_id: str, stars: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить через LOLZTEAM",
                    url=f"https://lolz.guru/market/balance/transfer?payment_id={payment_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить статус оплаты",
                    callback_data=f"check_payment:{payment_id}:{stars}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="main_menu"
                )
            ]
        ]
    )

def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="⭐ Выдать звёзды", callback_data="admin_gift"),
                InlineKeyboardButton(text="📈 Топы", callback_data="admin_top")
            ],
            [
                InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")
            ]
        ]
    )