from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я эхо-бот. Напиши мне что-нибудь, и я повторю это.\n"
        "Команды: /start, /help"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Доступные команды:\n"
        "/start — приветствие\n"
        "/help — это сообщение\n\n"
        "Любое другое сообщение я просто повторю."
    )


@router.message()
async def echo(message: Message) -> None:
    await message.answer(message.text or "Я умею отвечать только на текстовые сообщения.")
