import asyncio
import html
import json
import logging
import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from questionnaire import handle_answer, handle_fill_form, restart_test

# Prefer process environment (e.g. Docker `env_file`) and only fallback to local .env.
if os.getenv("TOKEN") is None:
    load_dotenv(".env")

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ADMIN_IDS", "").split(",")
    if user_id.strip().isdigit()
}
SHOP_WEB_APP_URL = os.getenv("SHOP_WEB_APP_URL")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main_keyboard(user_telegram_id: int) -> ReplyKeyboardMarkup:
    shop_button = (
        KeyboardButton(text="🛒 Магазин", web_app=WebAppInfo(url=SHOP_WEB_APP_URL))
        if SHOP_WEB_APP_URL
        else KeyboardButton(text="🛒 Магазин")
    )

    buttons = [
        [KeyboardButton(text="🧴 Подобрать уход"), KeyboardButton(text="🗓️ Запись")],
        [shop_button, KeyboardButton(text="❓ Помощь")],
    ]

    if user_telegram_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text="⚙️ Админ панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,  # keep buttons visible after re-entering the chat
        input_field_placeholder="Воспользуйтесь меню:",
    )


async def start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    await message.answer("Привет! Выберите интересующую опцию:", reply_markup=main_keyboard(user_id))


async def handle_booking_request(message: Message) -> None:
    await message.answer("Онлайн-запись появится совсем скоро. Спасибо за ожидание!")


async def show_shop(message: Message) -> None:
    if not SHOP_WEB_APP_URL:
        await message.answer(
            "Магазин временно недоступен. Пожалуйста, попробуйте позже."
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть мини-магазин",
                    web_app=WebAppInfo(url=SHOP_WEB_APP_URL),
                )
            ]
        ]
    )

    await message.answer(
        "Жмите на кнопку ниже, чтобы открыть мини-магазин и оформить заказ.",
        reply_markup=keyboard,
    )


async def handle_shop_order(message: Message) -> None:
    if not message.web_app_data or not message.web_app_data.data:
        await message.answer("Не удалось получить данные заказа.")
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        logger.exception("Failed to decode web_app_data payload: %s", message.web_app_data.data)
        await message.answer("Произошла ошибка при обработке заказа.")
        return

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        await message.answer("Похоже, корзина была пустой — заказ не создан.")
        return

    def _to_decimal(value) -> Decimal | None:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    order_lines = []
    total_calculated = Decimal("0")

    for idx, raw_item in enumerate(items, start=1):
        name = str(raw_item.get("name", "Без названия"))
        quantity_raw = raw_item.get("quantity", 0)
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0

        price = _to_decimal(raw_item.get("price")) or Decimal("0")
        line_total = price * quantity
        total_calculated += line_total

        order_lines.append(
            f"{idx}. {html.escape(name)} — {quantity} шт. x ${price:.2f} = ${line_total:.2f}"
        )

    declared_total = _to_decimal(payload.get("totalPrice"))
    total_display = declared_total if declared_total is not None else total_calculated

    if declared_total is not None and abs(declared_total - total_calculated) > Decimal("0.01"):
        logger.warning(
            "Order total mismatch for user %s: declared %s vs calculated %s",
            message.from_user.id if message.from_user else "unknown",
            declared_total,
            total_calculated,
        )
        order_lines.append(
            f"Пересчитанная сумма: ${total_calculated:.2f} (передано: ${declared_total:.2f})"
        )
        total_display = total_calculated

    order_text = "\n".join(order_lines)
    user_note = (
        "<b>Спасибо!</b>\n"
        "Запрос на оформление заказа передан.\n\n"
        f"{order_text}\n"
        f"<b>Итого:</b> ${total_display:.2f}"
    )
    await message.answer(user_note)

    if ADMIN_IDS:
        user = message.from_user
        user_link = "неизвестный покупатель"
        if user:
            escaped_name = html.escape(user.full_name or str(user.id))
            user_link = f"<a href='tg://user?id={user.id}'>{escaped_name}</a>"

        admin_text = (
            f"🛒 <b>Новый заказ</b>\n"
            f"Покупатель: {user_link}\n"
            f"{order_text}\n"
            f"<b>Итого:</b> ${total_display:.2f}"
        )

        for admin_id in ADMIN_IDS:
            if user and admin_id == user.id:
                continue
            try:
                await message.bot.send_message(admin_id, admin_text)
            except Exception:
                logger.exception("Failed to notify admin %s about new order.", admin_id)


async def show_help(message: Message) -> None:
    help_text = (
        "<b>Нужна подсказка?</b>\n\n"
        "Вы можете подобрать уход в зависимости от того, насколько хорошо понимаете особенности своей кожи:\n"
        "• <b>Подобрать уход</b> — тест на определение типа кожи и профессиональные рекомендации.\n"
        "• <b>Запись</b> — перейдите сюда, если хотите сразу пообщаться с косметологом.\n"
        "• <b>Магазин</b> — загляните, чтобы заказать конкретное средство."
    )
    await message.answer(help_text)


async def show_admin_panel(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if user_id in ADMIN_IDS:
        await message.answer("Админ-панель пока что пуста, но мы уже над ней работаем.")
    else:
        await message.answer("У вас нет доступа к админ-панели.")


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("Не удалось получить TOKEN из переменных окружения.")

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(start, CommandStart())
    dp.message.register(handle_shop_order, F.web_app_data)
    dp.message.register(handle_fill_form, F.text == "🧴 Подобрать уход")
    dp.message.register(handle_booking_request, F.text == "🗓️ Запись")
    dp.message.register(show_shop, F.text == "🛒 Магазин")
    dp.message.register(show_help, F.text == "❓ Помощь")
    dp.message.register(show_admin_panel, F.text == "⚙️ Админ панель")
    dp.callback_query.register(restart_test, F.data == "restart_test")
    dp.callback_query.register(handle_answer, F.data.regexp(r"^(answer|toggle|next):"))

    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
