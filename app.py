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
batalion = sh.worksheet("Батальон")
buton_number = 20
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

async def atack_time(update: Update,context):
    user_id = update.effective_user.id
    for grops_name in data["grops"]:
        worksheet = sh.worksheet((str(grops_name)))
        if worksheet.find(str(user_id),in_column=14) != None:
            await update.message.reply_text("Прова найдены напишите текст для атаки")
            context.user_data["atack"] = 1
            return
    await update.message.reply_text("лох")
#Обработка текста
async def message(update: Update,context):
    user_id = update.effective_user.id
    state = context.user_data.get("atack")
    if state is None:
        return
    user_text = update.message.text
    user_data= context.user_data["atack"]
    del context.user_data["atack"]
    context.user_data.clear
    if user_data == 1:
        context.user_data["text"] = user_text
        keyboard = []
        i = 0
        for grops_name in data["grops"]:
                worksheet = sh.worksheet(str(grops_name))
                if worksheet.find(str(user_id),in_column=14) != None:
                    keyboard.append([(grops_name)])
                    i = i+1
        reply_markup = ReplyKeyboardMarkup(keyboard)
        await update.message.reply_text("текст получен выберите где будет призыв", reply_markup=reply_markup)
        context.user_data["atack"] = 2
    if user_data == 3:
        global buton_number
        text = context.user_data["text"] 
        del context.user_data["text"]
        i = 1
        worksheet = sh.worksheet(str(context.user_data["grops"]))
        del context.user_data["grops"]
        context.user_data.clear
        context.bot_data["second_texts"] = []
        context.bot_data["second_texts"].append(user_text)
        keyboard =[
             [InlineKeyboardButton("Подробности",callback_data=buton_number)]
        ]
        buton_number = buton_number + 1
        reply_markup = InlineKeyboardMarkup(keyboard)
        id_messag =worksheet.cell(1,1).value
        while id_messag != None:
                    await context.bot.send_message(
                    chat_id=id_messag,
                    text = text,
                    reply_markup = reply_markup
                )
                    i = i+1
                    id_messag =worksheet.cell(i,1).value
        await update.message.reply_text("Призыв окончен")
    if user_data == 2:
        context.user_data["grops"] = user_text
        await update.message.reply_text("Вы выбрали взвод, напишите текст который будет высвечиватся после")
        context.user_data["atack"] = 3

#Кнопки
async def button(update: Update,context):
    query = update.callback_query
    variant = query.data
    if int(variant) >= 20: 
        new_text = int(variant) - 20
        await query.edit_message_text(context.bot_data["second_texts"][new_text])



#кнопкпи
def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start",start))
    application.add_handler(CommandHandler("my_id",my_id))
    application.add_handler(CommandHandler("atack_time",atack_time))
    #оброботка текста
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    #кнопки
    application.add_handler(CallbackQueryHandler(button))
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()