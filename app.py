import json
import uuid
import gspread
import logging
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup,ReplyKeyboardMarkup
from telegram.error import BadRequest, TelegramError
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
logger.addHandler(handler)
#Настройка гугл таблиц
gc = gspread.oauth()
sh = gc.open("Батальоны и взводы")
post_ch = gc.open("42_pasta")
report_ch = gc.open("Отчёты")
worksheet_post = post_ch.worksheet("42")
worksheet_42 = post_ch.worksheet("42")
worksheet_stats = post_ch.worksheet("Лист2")
worksheet_top = post_ch.worksheet("Рейтинг")
batalion = sh.worksheet("Батальон")

#Команды
async def start(update: Update, context):
    user_id = update.effective_user.id
    if worksheet_stats.find(str(user_id)) == None:
            worksheet_stats.append_row([user_id,"",""])
    platoon = []
    for grops_name in data["grops"]:
            group_id = data["grops"][grops_name]
            worksheet = sh.worksheet(str(grops_name))

            # В некоторых группах Telegram может вернуть BadRequest
            # (например, "Member not found"), если пользователь не найден
            # или бот не может проверить его членство. Пропускаем такой чат,
            # чтобы /start продолжал работать с остальными взводами.
            try:
                member = await context.bot.get_chat_member(
                    chat_id=group_id,
                    user_id=int(user_id)
                )
            except BadRequest as exc:
                logger.warning(
                    "Не удалось проверить членство user_id=%s в группе %s (%s): %s",
                    user_id, grops_name, group_id, exc
                )
                continue
            except TelegramError:
                logger.exception(
                    "Ошибка Telegram при проверке членства user_id=%s в группе %s",
                    user_id, grops_name
                )
                continue

            if member.status in ['creator', 'administrator', 'member']:
                if worksheet.find(str(user_id)) is None:
                    worksheet.append_row((str(user_id), update.effective_user.first_name))
                platoon.append(grops_name)
    await update.message.reply_text(f"Привет \nТы можешь посмотерть пасты на /post или используй /help \n  Ты был записан в \n{platoon}")
async def help(update,context): 
        message = update.message
        await message.reply_text(
        "Привет, тут я постораюсь ответить на самые частые вопросы.\n"
        "Код проекта:https://github.com/123myr123/fugapostobt_tgbot/tree/main\n"
        "Список паст из /post обьединеный в гугл таблицу: https://docs.google.com/spreadsheets/d/e/2PACX-1vRAAd_FUx7BD9kQN37XBJIf6YlNmexV4CL0D5S8GDEwhyM7JBV0FUd8DC_feihOvzL1lPd4xGikJvpt/pubhtml"
        "\nКаналл с новостями по боту: https://t.me/fugapostnews"
        )
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
            group_id = data["grops"][grops_name]
            try:
                member = await context.bot.get_chat_member(
                    chat_id=group_id,
                    user_id=int(user_id)
                )
            except BadRequest as exc:
                logger.warning(
                    "Не удалось проверить членство user_id=%s в группе %s (%s): %s",
                    user_id, grops_name, group_id, exc
                )
                continue
            except TelegramError:
                logger.exception(
                    "Ошибка Telegram при проверке членства user_id=%s в группе %s",
                    user_id, grops_name
                )
                continue
            if member.status in ['creator', 'administrator']:
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

async def check(update: Update,context):
    message = update.effective_message

    if not message:
        return

    target_user = None
    platoon = []

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        for grops_name in data["grops"]:
            worksheet = sh.worksheet(str(grops_name))
            if worksheet.find(str(target_user.id)) != None:
                platoon.append(grops_name)
        if platoon == []:
            await message.reply_text("Пользователь нигде не найден, скорее всего он не запускал бота")
        else:
            await message.reply_text(f"Пользователь найден в {platoon}")

async def  report_start(update: Update,context):
    user_id = update.effective_user.id
    for grops_name in data["grops"]:
            group_id = data["grops"][grops_name]
            try:
                member = await context.bot.get_chat_member(
                    chat_id=group_id,
                    user_id=int(user_id)
                )
            except BadRequest as exc:
                logger.warning(
                    "Не удалось проверить членство user_id=%s в группе %s (%s): %s",
                    user_id, grops_name, group_id, exc
                )
                continue
            except TelegramError:
                logger.exception(
                    "Ошибка Telegram при проверке членства user_id=%s в группе %s",
                    user_id, grops_name
                )
                continue
            if member.status in ['creator', 'administrator']:
                await update.message.reply_text("Прова найдены напишите название отчета")
                context.user_data["report_start"] = 1
                return
    await update.message.reply_text("лох")

async def report(update: Update,context):
    report = context.bot_data.get("report")
    if report == None:
        return
    user_id = update.effective_user.id
    keyboard = []
    for grops_name in data["grops"]:
                group_id = data["grops"][grops_name]
                worksheet = sh.worksheet(str(grops_name))
    
                # В некоторых группах Telegram может вернуть BadRequest
                # (например, "Member not found"), если пользователь не найден
                # или бот не может проверить его членство. Пропускаем такой чат,
                # чтобы /start продолжал работать с остальными взводами.
                try:
                    member = await context.bot.get_chat_member(
                        chat_id=group_id,
                        user_id=int(user_id)
                    )
                except BadRequest as exc:
                    logger.warning(
                        "Не удалось проверить членство user_id=%s в группе %s (%s): %s",
                        user_id, grops_name, group_id, exc
                    )
                    continue
                except TelegramError:
                    logger.exception(
                        "Ошибка Telegram при проверке членства user_id=%s в группе %s",
                        user_id, grops_name
                    )
                    continue
    
                if member.status in ['creator', 'administrator', 'member']:
                    if worksheet.find(str(user_id)) is None:
                        worksheet.append_row((str(user_id), update.effective_user.first_name))
                    keyboard.append([(grops_name)])
    reply_markup = ReplyKeyboardMarkup(keyboard)
    context.user_data["report"] = 1
    await update.message.reply_text("Сбор отчётов видется выберите взвод",reply_markup=reply_markup)

#Обработка текста
async def message(update: Update,context):
    user_text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get("atack")
    report = context.user_data.get("report_start")
    User_report = context.user_data.get("report")
    if User_report != None:
         if User_report == 1:
              try:
                   report = context.bot_data.get("report")
                   id  = next(iter(data.values()), [None])
                   context.user_data["report"] = 2
                   context.user_data["report_table"] = id
                   await update.message.reply_text("Отправте фото и число(ТОЛЬКО ЧИСЛО)")
              except KeyError:
                    await update.message.reply_text("ЭТОТ ВЗВОД НЕ СОБИРАЕТ ОТЧЁТЫ")
         if User_report == 2:
            id = context.user_data["report_table"]
            worksheet = report_ch.worksheet(id)
            worksheet.append_rows([str(user_id),str(user_text),str(update.message.id)])
            await update.message.reply_text("Ваш отчет зафиксирован")

              
    if report != None:
        if report == 2:
            tema = context.user_data["text"]
            del  context.user_data["text"]
            await update.message.reply_text("Начинаю подготовку ко сбору отчетов")
            del context.user_data["report_start"]
            worksheet_id = uuid.uuid4().hex[:12]
            worksheet =report_ch.add_worksheet(worksheet_id,500,20)
            worksheet_idfilter = uuid.uuid4().hex[:12]
            worksheet =report_ch.add_worksheet(worksheet_idfilter,500,20)
            context.bot_data["report"] = {user_text:[worksheet_id]}
            worksheet = sh.worksheet(str(user_text))
            id_messag = worksheet.cell(1,1).value
            i = 1
            while id_messag != None:
                    try:
                        await context.bot.send_message(
                    chat_id=id_messag,
                    text = "Начался сбор отчётов команда /report доступна в течении 12 часов"
                    f"\nТЕМА ОТЧЁТОВ:{tema}"
                )
                        i = i+1
                    except:
                        i = i+1
                    id_messag =worksheet.cell(i,1).value
            context.job_queue.run_once(finalizing_reports, 120, data=[worksheet_id], chat_id=user_id)
            await update.message.reply_text("Подготовка завершина, сбор начат")
              
        elif report ==1:
            context.user_data["text"] = user_text
            keyboard = []
            i = 0
            for grops_name in data["grops"]:
                group_id = data["grops"][grops_name]
                try:
                    member = await context.bot.get_chat_member(
                                chat_id=group_id,
                                user_id=int(user_id)
                            )
                except BadRequest as exc:
                            logger.warning(
                                "Не удалось проверить членство user_id=%s в группе %s (%s): %s",
                                user_id, grops_name, group_id, exc
                            )
                            continue
                except TelegramError:
                            logger.exception(
                                "Ошибка Telegram при проверке членства user_id=%s в группе %s",
                                user_id, grops_name
                            )
                            continue
                if member.status in ['creator', 'administrator']:
                    keyboard.append([(grops_name)])
                    reply_markup = ReplyKeyboardMarkup(keyboard)
                    await update.message.reply_text("Выберите где будут собератся отчеты", reply_markup=reply_markup)
                    context.user_data["report_start"] = 2
                    return

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
            group_id = data["grops"][grops_name]
            try:
                member = await context.bot.get_chat_member(
                    chat_id=group_id,
                    user_id=int(user_id)
                )
            except BadRequest as exc:
                logger.warning(
                    "Не удалось проверить членство user_id=%s в группе %s (%s): %s",
                    user_id, grops_name, group_id, exc
                )
                continue
            except TelegramError:
                logger.exception(
                    "Ошибка Telegram при проверке членства user_id=%s в группе %s",
                    user_id, grops_name
                )
                continue
            if member.status in ['creator', 'administrator']:
                keyboard.append([(grops_name)])
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
        context.bot_data["second_texts"][details_id] = {
            "text": user_text,
            "worksheet": worksheet.title,
        }

        keyboard = [
            [InlineKeyboardButton(
                "Подробности",
                callback_data=f"detail:{details_id}"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        id_messag =worksheet.cell(1,1).value
        while id_messag != None:
                    try:
                        await context.bot.send_message(
                    chat_id=id_messag,
                    text = text,
                    reply_markup = reply_markup
                )
                        i = i+1
                    except:
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
    await query.answer()

    # Кнопки подробностей новых призывов используют уникальный ID.
    if variant.startswith("detail:"):
        details_id = variant.split(":", 1)[1]
        details = context.bot_data.get("second_texts", {}).get(details_id)

        if not details:
            await query.edit_message_text(
                "Подробности этого призыва больше недоступны."
            )
            return

        # Учитываем нажатие в листе именно того взвода,
        # для которого был отправлен этот призыв.
        user_id = str(query.from_user.id)
        platoon_sheet = sh.worksheet(details["worksheet"])
        member_cell = platoon_sheet.find(user_id, in_column=1)

        if member_cell is None:
            await query.answer(
                "Не удалось найти вас в таблице этого взвода.",
                show_alert=True
            )
            return

        # Увеличиваем значение в третьем столбце строки пользователя на 1.
        count_cell = platoon_sheet.cell(member_cell.row, 3).value
        try:
            count = int(count_cell) if count_cell not in (None, "") else 0
        except (TypeError, ValueError):
            await query.answer(
                "В третьем столбце указано не число.",
                show_alert=True
            )
            return

        platoon_sheet.update_cell(member_cell.row, 3, count + 1)

        await query.edit_message_text(details["text"])
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
            )
        return
# Очистака памяти каждые 24 часа
async def clear_data_bot(context):
    context.bot_data.clear()
# завершение таблицы и перессылка сообщений
async def finalizing_reports(context):
    table = context.job.data
    await context.bot.send_message(chat_id=context.job.chat_id, text=f'Сбор окончен')
    await context.bot.send_message(chat_id=context.job.chat_id, text = f"{table[0]}")



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
    application.add_handler(CommandHandler("help",help))
    application.add_handler(CommandHandler("check",check))
    application.add_handler(CommandHandler("report_start",report_start))
    application.add_handler(CommandHandler("report",report))
    #оброботка текста
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    #кнопки
    application.add_handler(CallbackQueryHandler(button))
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()