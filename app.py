import json
import gspread
import logging
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup,ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes,CallbackQueryHandler
from logging.handlers import RotatingFileHandler
#Копирование токена из json
file = open("settings.json",'r',encoding="UTF-8")
data = json.load(file)
TOKEN = data["TOKEN"]

# Настройка логирования
logger = logging.getLogger()
handler = RotatingFileHandler("app.log", maxBytes=1_024_1024, backupCount=1, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
handler.setFormatter(formatter)
#Настройка гугл таблиц
gc = gspread.oauth()
sh = gc.open("Батальоны и взводы")
batalien = sh.worksheet("БАТАЛЬОН")

async def start(update: Update, context):
    if batalien.find(str(update.effective_user.id)) == None:
        batalien.append_row([update.effective_user.id,update.effective_user.first_name])
    await update.message.reply_text("Привет, ты был записан в первый батальён, \nТы можешь посмотерть пасты на /post или используй /help \n Если ты состоишь в какомто взводе то используй /platoon")
async def platoon(update: Update, context):
    keyboard =[
        [  
        InlineKeyboardButton("1Взвод",callback_data=1),
        InlineKeyboardButton("2Взвод",callback_data=2),
        InlineKeyboardButton("3Взвод",callback_data=3),
        InlineKeyboardButton("4Взвод",callback_data=4),
        InlineKeyboardButton("5Взвод",callback_data=5)
        ]
        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери взвод в ктором ты состоишь", reply_markup=reply_markup)

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
    application.add_handler(CommandHandler("platoon",platoon))
    #кнопки
    application.add_handler(CallbackQueryHandler(buton))
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()