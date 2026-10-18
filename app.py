import json
import gspread
import logging
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup,ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes,CallbackQueryHandler
from logging.handlers import RotatingFileHandler
#Копирование токена из json
file = open("settings.json",'r',encoding="UTF-8")
data = json.load(file)
file.close()
TOKEN = data["TOKEN"]

# Настройка логирования
logger = logging.getLogger()
handler = RotatingFileHandler("app.log", maxBytes=1_024_1024, backupCount=1, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
handler.setFormatter(formatter)
#Настройка гугл таблиц
gc = gspread.oauth()
sh = gc.open("Батальоны и взводы")

async def start(update: Update, context):
    user_id = update.effective_user.id
    group_id = data["grops"]["Батальон"]
    member = await context.bot.get_chat_member(
    chat_id=group_id,
    user_id=int(user_id)
    )
    if member.status in ['creator', 'administrator', 'member']:
        platoon = []
        for grops_name in data["grops"]:
            group_id = data["grops"][grops_name]
            member = await context.bot.get_chat_member(
                chat_id=group_id,
                user_id=int(user_id)
                )
            worksheet = sh.worksheet(str(grops_name))
            if member.status in ['creator', 'administrator', 'member']:
                if worksheet.find(str(user_id)) == None:
                    worksheet.append_row((str(user_id),update.effective_user.first_name))
                platoon.append(grops_name)
        await update.message.reply_text(f"Привет, ты был записан в первый батальён, \nТы можешь посмотерть пасты на /post или используй /help \n Если ты был записан в \n   {platoon}")
    else:
        await update.message.reply_text("ТЫ ДАЖЕ НЕ ГРАЖДАНИН")
async def my_id(update: Update,context):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    group = update.effective_chat.id
    await update.message.reply_text(f"Привет, {user_name}! Твой ID: {user_id}, ID групы:{group}")

#кнопкпи
async def buton(update: Update, context):
    query = update.callback_query
    variant = query.data
    if int(variant) <= 5:
        worksheet = sh.worksheet(str(variant))
        worksheet.append_row([update.effective_user.id,update.effective_user.first_name])
        await query.edit_message_text(f"Ты добавлен в {variant} взвод")
        return

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start",start))
    application.add_handler(CommandHandler("my_id",my_id))
    #кнопки
    application.add_handler(CallbackQueryHandler(buton))
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()