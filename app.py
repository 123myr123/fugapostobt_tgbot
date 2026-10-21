import json
import uuid
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
handler = RotatingFileHandler("app.log", maxBytes=1_024_1024, backupCount=2, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
handler.setFormatter(formatter)
#Настройка гугл таблиц
gc = gspread.oauth()
sh = gc.open("Батальоны и взводы")
post_ch = gc.open("42_pasta")
worksheet_post = post_ch.worksheet("42")
worksheet_42 = post_ch.worksheet("42")
worksheet_stats = post_ch.worksheet("Лист2")
worksheet_top = post_ch.worksheet("Рейтинг")
batalion = sh.worksheet("Батальон")
async def start(update: Update, context):
    user_id = update.effective_user.id
    group_id = data["grops"]["Батальон"]
    member = await context.bot.get_chat_member(
    chat_id=group_id,
    user_id=int(user_id)
    )
    if worksheet_stats.find(str(user_id)) == None:
            worksheet_stats.append_row([user_id,"",""])
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
async def add_post(update: Update,context):
    button_list = [
        InlineKeyboardButton("Отменить отправку", callback_data="No"),
    ]
    reply_markup = InlineKeyboardMarkup(build_menu(button_list,n_cols=1))
    context.user_data.clear
    context.user_data["post_add"] = True
    await update.message.reply_text("Для сохранения пасты скиньте её текст следующим сообщением.",reply_markup=reply_markup)
async def atack_time(update: Update,context):
    user_id = update.effective_user.id
    for grops_name in data["grops"]:
        worksheet = sh.worksheet((str(grops_name)))
        if worksheet.find(str(user_id),in_column=14) != None:
            await update.message.reply_text("Прова найдены напишите текст для атаки")
            context.user_data["atack"] = 1
            return
    await update.message.reply_text("лох")
async def post(update:Update, context):
    keyboard = [
                [
                InlineKeyboardButton("Следущюя", callback_data='+'),
                ],
                [
                InlineKeyboardButton("1🌟", callback_data='1'),
                InlineKeyboardButton("2🌟", callback_data='2'),
                InlineKeyboardButton("3🌟", callback_data='3'),
                InlineKeyboardButton("4🌟", callback_data='4'),
                InlineKeyboardButton("5🌟", callback_data='5'),
                ]
            ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    post = worksheet_42.cell(1, 1).value
    context.user_data["post"] = 1
    await update.message.reply_text(f"{post}",reply_markup=reply_markup)
async def top_post(update: Update,context):
    values_list = worksheet_top.col_values(2)
    values_list.sort(reverse=True)
    top_past =  worksheet_top.find(values_list[0])
    keyboard = [
                [
                InlineKeyboardButton("Следущюя", callback_data='++'),
                ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data["post"] = 0
    await update.message.reply_text(f"{worksheet_top.cell(top_past.row,1).value}",reply_markup=reply_markup)
#Обработка текста
async def message(update: Update,context):
    user_id = update.effective_user.id
    state = context.user_data.get("atack")
    if state is None:
        state = context.user_data.get("post_add")
        if state is None:
            return
        if context.user_data["post_add"] == True:
            del context.user_data["post_add"]
            context.user_data.clear()
            await message.reply_text("Паста добавлена")
            values = [user_text,"",""]
            worksheet_42.append_row(values)
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
        text = context.user_data["text"]
        del context.user_data["text"]
        i = 1
        worksheet = sh.worksheet(str(context.user_data["grops"]))
        del context.user_data["grops"]
        context.user_data.clear

        # Сохраняем подробности отдельно для каждого призыва.
        details_id = uuid.uuid4().hex[:12]
        context.bot_data.setdefault("second_texts", {})
        context.bot_data["second_texts"][details_id] = user_text

        keyboard = [
            [InlineKeyboardButton(
                "Подробности",
                callback_data=f"detail:{details_id}"
            )]
        ]
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
    state = context.user_data.get("post_add")
    

#Кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    variant = query.data
    print(variant)
    await query.answer()

    # Кнопки подробностей новых призывов используют уникальный ID.
    if variant.startswith("detail:"):
        details_id = variant.split(":", 1)[1]
        details = context.bot_data.get("second_texts", {}).get(details_id)
        await query.edit_message_text(
            details or "Подробности этого призыва больше недоступны."
        )
        return
    if variant =="++":
        post =context.user_data["post"]
        del context.user_data["post"]
        keyboard = [
                    [
                    InlineKeyboardButton("Прошлая", callback_data='--'),
                    InlineKeyboardButton("Следющая", callback_data='++'),
                    ]
                ]
        values_list = worksheet_top.col_values(2)
        values_list.sort(reverse=True)
        top_past =  worksheet_top.find(values_list[post + 1])
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data["post"] = post + 1
        await query.edit_message_text(f"{worksheet_top.cell(top_past.row,1).value}",reply_markup=reply_markup)
        return
    if variant =="--":
            post =context.user_data["post"]
            del context.user_data["post"]
            keyboard = [
                        [
                        InlineKeyboardButton("Прошлая", callback_data='--'),
                        InlineKeyboardButton("Следющая", callback_data='++'),
                        ]
                    ]
            values_list = worksheet_top.col_values(2)
            values_list.sort(reverse=True)
            top_past =  worksheet_top.find(values_list[post - 1])
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.user_data["post"] = post - 1
            await query.edit_message_text(f"{worksheet_top.cell(top_past.row,1).value}",reply_markup=reply_markup)
            return
    
    try:
        if int(variant) <= 5:
            post = context.user_data["post"]
            del context.user_data["post"]
            i = int(post)
            context.user_data["post"] = i
            post = worksheet_42.cell(i, 1).value
            text =worksheet_stats.find(post)
            user = worksheet_stats.find(str(update.effective_user.id))
            worksheet_stats.update_cell(user.row,text.col,variant)
            await context.bot.send_message(chat_id = update.effective_user.id, text="Ваша оценка добавлена/изменина")
            keyboard = [
                    [
                    InlineKeyboardButton("Прошлая", callback_data='-'),
                    InlineKeyboardButton("Следющая", callback_data='+'),
                    ]
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"{post}",reply_markup=reply_markup)
            return
    except:
        post = 1
    if variant == "No":
        del context.user_data["post_add"]
        context.user_data.clear()
        await query.edit_message_text("Отправка отменина")
        return
    elif variant == "+" or variant == "-":
        try:
            post = context.user_data["post"]
            if variant == "+":
                del context.user_data["post"]
                i = int(post) + 1
                post = worksheet_42.cell(i, 1).value
                context.user_data["post"] = i
                if post == None:
                  post = worksheet_42.cell(1, 1).value
                  del context.user_data["post"]
                  context.user_data["post"] = 1
            else:
                del context.user_data["post"]
                i = int(post) - 1
                post = worksheet_42.cell(i, 1).value
                context.user_data["post"] = i
                if post == None:
                    del context.user_data["post"]
                    context.user_data["post"] = 1
        except:
            post = "Ошибка на стороне сервера попробуйте познее"
        keyboard = [
            [
            InlineKeyboardButton("Прошлая", callback_data='-'),
            InlineKeyboardButton("Следющая", callback_data='+'),
            ],
            [
            InlineKeyboardButton("1🌟", callback_data='1'),
            InlineKeyboardButton("2🌟", callback_data='2'),
            InlineKeyboardButton("3🌟", callback_data='3'),
            InlineKeyboardButton("4🌟", callback_data='4'),
            InlineKeyboardButton("5🌟", callback_data='5'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"{post}",reply_markup=reply_markup)
    # Совместимость со старыми сообщениями, отправленными до обновления.
    if variant.isdigit() and int(variant) >= 20:
        new_text = int(variant) - 20
        old_texts = context.bot_data.get("second_texts", [])
        if isinstance(old_texts, list) and 0 <= new_text < len(old_texts):
            await query.edit_message_text(old_texts[new_text])
        else:
            await query.edit_message_text(
                "Подробности этого старого призыва недоступны. "
                "Для новых призывов кнопка будет работать."
            )
        return
# Очистака памяти каждые 24 часа
async def clear_data_bot(context):
    context.bot_data.clear()


#кнопкпи
def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TOKEN).build()
    #очистка памяти
    job_queue = application.job_queue
    job_queue.run_repeating(clear_data_bot, interval=172800, first=10)
    # Команды
    application.add_handler(CommandHandler("start",start))
    application.add_handler(CommandHandler("my_id",my_id))
    application.add_handler(CommandHandler("atack_time",atack_time))
    application.add_handler(CommandHandler("post",post))
    application.add_handler(CommandHandler("add_post",add_post))
    application.add_handler(CommandHandler("top_post",top_post))
    #оброботка текста
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    #кнопки
    application.add_handler(CallbackQueryHandler(button))
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()