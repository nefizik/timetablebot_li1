import logging
import telegram
import sqlite3
import datetime
import hashlib
import shutil

from openpyxl import load_workbook
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# dont forget to create list so that not call base a lot

# classes_list return list of classes prepared for making keyboard
def classes_list():
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()

    cursor_execution_result = cur.execute('select class_, letter from classes_ order by class_;').fetchall()
    keyboard = [[]]

    cursor_execution_result_size = len(cursor_execution_result)

    i = 0
    j = 0
    while i < cursor_execution_result_size:
        keyboard.append([])
        while j < cursor_execution_result_size and cursor_execution_result[j][0] == cursor_execution_result[i][0]:
            keyboard[i + 1].append(str(cursor_execution_result[j][0])
                                   + cursor_execution_result[j][1])
            j += 1
        i += 1

    con.close()
    return keyboard


# weekday_list return list of weekdays prepared for making keyboard
def weekday_list():
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()
    cursor_execution_result = cur.execute('select weekday from Weekdays order by id;').fetchall()
    keyboard = [[]]
    i = 0
    j = 0
    keyboard.append([])

    for row in cursor_execution_result:
        keyboard[i + 1].append(str(*cursor_execution_result[2 * i + j]))
        j += 1
        if j == 2:
            j = 0
            i += 1
            keyboard.append([])

    con.close()
    return keyboard


# teachers_list return list of teachers
def teachers_list():
    # take teachers list from database and make the list
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()

    cursor_execution_result = cur.execute('select SNF from Teachers order by SNF;').fetchall()
    teach_keyboard = []

    for row in cursor_execution_result:
        teach_keyboard.append(row)

    con.close()
    return teach_keyboard


def is_weekday(update, context):
    a = weekday_list()
    for i in range(0, len(a)):
        for j in range(0, len(a[i])):
            if update.message.text == a[i][j]:
                return True
    return False


def is_student(update, context):
    a = classes_list()
    for i in range(0, len(a)):
        for j in range(0, len(a[i])):
            if update.message.text == a[i][j]:
                return True
    return False


def is_teacher(update, context):
    a = teachers_list()
    for i in range(0, len(a)):
        if update.message.text == a[i][0]:
            return True
    return False


def class_selection_menu(update, context):
    markup = telegram.ReplyKeyboardMarkup([['Я учитель']] + classes_list(), one_time_keyboard=True)
    update.message.reply_text('Здравствуй!\nВыбери свой класс из списка ниже.', reply_markup=markup)


def teacher_selection_menu(update, context):
    teach_markup = telegram.ReplyKeyboardMarkup(teachers_list(), one_time_keyboard=True)
    update.message.reply_text('Выберите свое имя в списке ниже.\nНе учитель? Нажмите /start чтобы начать сначала.',
                              reply_markup=teach_markup)


def weekday_selection_menu(update, context):
    markup = telegram.ReplyKeyboardMarkup([['Сегодня'], ['Завтра']] + weekday_list() + [['Расписание звонков']],
                                          one_time_keyboard=False)
    update.message.reply_text('Успешно!\nВыбрать класс заново? /start', reply_markup=markup)


# return id of class
def class_to_id(class_):
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()
    if len(class_) == 3:
        letter = class_[2]
        digits = class_[0] + class_[1]
    else:
        letter = class_[1]
        digits = class_[0]
    uclass = cur.execute(
        f'select id from Classes_ where class_ == {int(digits)} and letter == "{letter}";').fetchone()
    con.close()
    return uclass[0]


def teacher_to_id(teacher):
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()
    uteacher = cur.execute(f'select id from Teachers where SNF == "{str(teacher)}"').fetchone()
    con.close()
    return uteacher[0]


# connect user(chat_id) and teacher in table "Users"
def teachers(update, context):
    user = str(update.message.chat_id)
    cur_teacher = teacher_to_id(update.message.text)

    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()

    isreg = cur.execute(f'select class_or_teacher from Users where chat_id == {user};').fetchone()
    if (isreg == None):
        cur.execute(f'INSERT INTO main.Users(chat_id, class_or_teacher, is_teacher) VALUES ({user}, {cur_teacher}, 1);')
    else:
        cur.execute(f'UPDATE Users SET class_or_teacher = {cur_teacher}, is_teacher = 1 WHERE chat_id == {user}')

    con.commit()
    con.close()

    weekday_selection_menu(update, context)


# connect user(chat_id) and class in table "Users"
def students(update, context):
    user = str(update.message.chat_id)
    cur_class = str(class_to_id(update.message.text))

    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()

    isreg = cur.execute(f'select class_or_teacher from Users where chat_id == {user};').fetchone()
    if (isreg == None):
        cur.execute(f'INSERT INTO main.Users(chat_id, class_or_teacher, is_teacher) VALUES ({user}, {cur_class}, 0);')
    else:
        cur.execute(f'UPDATE Users SET class_or_teacher = {cur_class}, is_teacher = 0 WHERE chat_id == {user}')

    con.commit()
    con.close()

    weekday_selection_menu(update, context)


def preprinting(update, context, day):
    if day == 8:
        day = 1
    if day == 7:
        update.message.reply_text("Урааа, выходной)")
    else:
        con = sqlite3.connect('BOTSBASE.db')
        cur = con.cursor()
        # get id of weekday
        if day == 0:
            weekday_id = cur.execute(
                f'select id from Weekdays where weekday == "{update.message.text}";').fetchone()[0]
        else:
            weekday_id = day
        str_weekday = cur.execute(f'select weekday from "main".Weekdays where id == {weekday_id}').fetchone()[0]
        print("weekday -", weekday_id)
        user = update.message.chat_id
        class_or_teacher = cur.execute(
            f'select class_or_teacher, is_teacher from Users WHERE chat_id == {user}').fetchone()
        con.close()

        if class_or_teacher[1] == 0:
            printing_for_students(update, context, weekday_id, class_or_teacher[0], str_weekday)
        else:
            printing_for_teachers(update, context, weekday_id, class_or_teacher[0], str_weekday)


def printing_for_teachers(update, context, weekday_id, teacher, str_weekday):
    con = sqlite3.connect("BOTSBASE_for_edit.db")
    cur = con.cursor()

    timetable = cur.execute(
        f'select class_, cab, lesson, lesson_number from main_timetable where teacher == {teacher} and weekday == {weekday_id} order by lesson_number;'
    ).fetchall()
    str_teacher = cur.execute(f'select surname_for_table from "main".Teachers where id == {teacher}').fetchone()[0]

    keyboard = f'*{str_weekday} - {str_teacher}*\n\n'
    i = 0
    if len(timetable) == 0:
        keyboard += "Нет уроков"
    while i < len(timetable):
        class_ = cur.execute(f'select class_, letter from Classes_ where id == {timetable[i][0]};').fetchone()
        class_ = str(class_[0]) + class_[1]
        cab = str(timetable[i][1])
        lesson = cur.execute(f'select lesson from Lessons where id = {timetable[i][2]};').fetchone()
        lesson_number = str(timetable[i][3])
        keyboard += f'{lesson_number}) {class_} - {lesson[0]} ({cab})\n'
        i += 1

    con.close()
    update.message.reply_text(keyboard, parse_mode='Markdown')


def printing_for_students(update, context, weekday_id, class_, str_weekday):
    con = sqlite3.connect("BOTSBASE_for_edit.db")
    cur = con.cursor()

    # get timetable for this weekday and class
    timetable = cur.execute(
        f'select lesson, cab, lesson_number from main_timetable where weekday == {weekday_id} and class_ == {class_} order by lesson_number;'
    ).fetchall()
    str_class = cur.execute(f'select class_, letter from Classes_ where id = {class_}').fetchone()
    str_class = str(str_class[0]) + str_class[1]

    keyboard = f'*{str_weekday} - {str_class}*\n\n'
    i = 0
    les_num = 1
    while i < len(timetable):
        keyboard += f"{les_num}) "
        lesson_name = cur.execute(
            f'select lesson from Lessons where id=={timetable[i][0]};').fetchone()
        if len(timetable) - i > 1:
            if timetable[i][2] == timetable[i + 1][2]:
                if timetable[i][0] != timetable[i + 1][0]:
                    lesson_name2 = cur.execute(
                        f'select lesson from Lessons where id=={timetable[i + 1][0]}').fetchone()
                    keyboard += f"{lesson_name[0]} ({timetable[i][1]}) / {lesson_name2[0]} ({timetable[i + 1][1]})\n"
                else:
                    keyboard += f"{lesson_name[0]} ({timetable[i][1]}) / ({timetable[i + 1][1]})\n"
                i += 2
                les_num += 1
                continue
        if timetable[i][1] == 0:
            keyboard += f"{lesson_name[0]}\n"
        else:
            keyboard += f"{lesson_name[0]} ({timetable[i][1]})\n"
        i += 1
        les_num += 1

    con.close()
    update.message.reply_text(keyboard, parse_mode='Markdown')


def is_the_password_correct(the_password):  # может использовать много памяти
    return hashlib.pbkdf2_hmac('sha256', the_password.encode('UTF-8'), b'PTS', 50) == \
           b'\x89@\xf5Hd\x1a9\xd7\xb1\x07\x03\x81\x07b\xe1\x80\xd4h`/\xde\x16\xd6\x95\x9fUh\x05\xd7\x991w'
    # distanceBetweenSUNandEARTHequals0MB


def add_to_admins(update, context):
    con = sqlite3.connect('BOTSBASE_for_edit.db')
    cur = con.cursor()
    user = update.message.chat_id
    cur.execute(f'INSERT INTO main.Admins(chat_id) VALUES ({user});')
    update.message.reply_text('Теперь вы можете вносить изменения в расписание набрав команду /edit')
    con.commit()
    con.close()


def is_admin(update, context):
    con = sqlite3.connect('BOTSBASE_for_edit.db')
    cur = con.cursor()
    user = update.message.chat_id
    is_adm = cur.execute(f'select chat_id from Admins WHERE chat_id == {user}').fetchone()
    con.close()
    if is_adm == None:
        return False
    else:
        return True


def from_table_to_base(update, context):
    wb = load_workbook('editing.xlsx')
    sheet = wb.active
    con = sqlite3.connect('BOTSBASE_for_edit.db')
    cur = con.cursor()

    teachers = cur.execute(
        f'select surname_for_table from Teachers order by surname_for_table;'
    ).fetchall()

    cur.execute(f'DELETE FROM main_timetable')

    for col in range(3, 3 * len(teachers) + 3, 3):
        teacher_cell = str(sheet.cell(row=1, column=col).value)
        teacher_id = cur.execute(f'select id from Teachers where surname_for_table == "{teacher_cell}"').fetchone()

        weekday = 1
        for week in range(2, 48, 9):
            for num in range(0, 9):
                lesson_cell = sheet.cell(column=col, row=week + num)
                lesson = lesson_cell.value
                if lesson != None:
                    lesson = cur.execute(f'select id from Lessons WHERE lesson == "{lesson}"').fetchone()

                    cab_cell = sheet.cell(column=col + 2, row=week + num)
                    cab = cab_cell.value

                    class_cell = sheet.cell(column=col + 1, row=week + num)
                    clas = class_cell.value
                    if len(clas) == 3:
                        digit = clas[0] + clas[1]
                        letter = clas[2]
                    else:
                        digit = clas[0]
                        letter = clas[1]
                    clas = cur.execute(
                        f'select id from Classes_ WHERE class_ == {int(digit)} AND letter == "{letter}"').fetchone()

                    lesson_num = sheet.cell(column=2, row=week + num).value
                    print(f'{teacher_id[0]}, {clas[0]}, {cab}, {lesson[0]}, {weekday}, {lesson_num}')
                    cur.execute(
                        f'INSERT INTO main_timetable (teacher, class_, cab, lesson, weekday, lesson_number) VALUES ({teacher_id[0]}, {clas[0]}, {cab}, {lesson[0]}, {weekday}, {lesson_num});'

                    )

            weekday += 1
    con.commit()
    con.close()
    update.message.text('Успешно')
    # wb.save('editing.xlsx')


def from_base_to_table(update, context):
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()
    wb = load_workbook('editing.xlsx')
    # will use copy of template
    sheet = wb.active

    teachers = cur.execute(
        f'select surname_for_table from Teachers order by surname_for_table'
    ).fetchall()

    # fill row with teachers
    tcol = 3
    for col in range(3, len(teachers) + 3):
        value = teachers[col - 3][0]
        sheet.merge_cells(start_row=1, end_row=1, start_column=tcol, end_column=tcol + 2)
        cell = sheet.cell(row=1, column=tcol)
        cell.value = value
        tcol += 3

    # fill timetable
    for col in range(3, 3 * len(teachers) + 3, 3):
        teacher_cell = str(sheet.cell(row=1, column=col).value)
        teacher_id = cur.execute(f'select id from Teachers where surname_for_table == "{teacher_cell}"').fetchone()

        weekday = 1
        for week in range(2, 48, 9):
            for num in range(0, 9):
                lesson_cell = sheet.cell(column=col, row=week + num)
                class_cell = sheet.cell(column=col + 1, row=week + num)
                cab_cell = sheet.cell(column=col + 2, row=week + num)
                lesson_num = sheet.cell(column=2, row=week + num).value
                lesson = cur.execute(
                    f'select lesson, class_, cab from main_timetable WHERE teacher={teacher_id[0]} AND weekday={weekday} AND lesson_number = {lesson_num};').fetchone()
                if lesson != None:
                    lesson_value = cur.execute(f'select lesson from Lessons WHERE id = {lesson[0]};').fetchone()
                    class_value = cur.execute(f'select class_, letter from Classes_ WHERE id = {lesson[1]};').fetchone()
                    lesson_cell.value = lesson_value[0]
                    class_cell.value = str(class_value[0]) + class_value[1]
                    cab_cell.value = lesson[2]
            weekday += 1
    con.close()
    wb.save('editing.xlsx')
    table_file = open('editing.xlsx', 'rb')
    update.message.reply_document(update.message.chat_id, table_file)
    # telegram.File.download()
    # update.message.document()


def download_photo(update, context):
    if is_admin(update, context):
        photo_file = update.message.photo[-1].get_file()
        photo_file.download('user_photo.jpg')
        confirm_to_send_photo(update, context)


def confirm_to_send_photo(update, context):
    markup = telegram.ReplyKeyboardMarkup([['Нет']] + [['Да, отправить фото']])
    update.message.reply_text('Вы дейстивтельно хотите отправить это фото всем пользователям?', reply_markup=markup)


def send_to_all_users(update, context, arg):
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()
    users = cur.execute(f'select chat_id from "main".Users').fetchall()
    if arg == 0:
        for i in range(0, len(users)):
            context.bot.send_photo(chat_id=users[i][0], photo=open('user_photo.jpg', 'rb'))
    else:
        f = open('alert.txt', 'r')
        text = f.read()
        f.close()
        for i in range(0, len(users)):
            context.bot.send_message(chat_id=users[i][0], text=text)
    weekday_selection_menu(update, context)


def confirm_to_send_text(update, context, text):
    if text[1] == ' ':
        text = text[2:]
    else:
        text = text[1:]
    markup = telegram.ReplyKeyboardMarkup([['Нет']] + [['Да, отправить текст']])
    update.message.reply_text('Вы дейстивтельно хотите отправить текст ниже всем пользователям?\n\n'
                              f'_{text}_', reply_markup=markup, parse_mode="Markdown")
    f = open('alert.txt', 'w')
    f.write(text)
    f.close()


def download_document(update, context):
    if is_admin(update, context):
        photo_file = update.message.document.get_file()
        photo_file.download('user_doc.xlsx')
        update.message.reply_text('Принято')


def send_table_to_admin(update, context):
    table = open('editing.xlsx', 'rb')
    context.bot.send_document(chat_id=update.message.chat_id, document=table)


def editing(update, context):
    if is_admin(update, context):
        update.message.reply_text('МЕНЮ редактирования расписания')
        markup = telegram.ReplyKeyboardMarkup(
            [['Скачать таблицу с расписанием']] + [['Изменить постоянное расписание']] + [['Оповестить всех (текст)']])
        update.message.reply_text(
            'Вы можете загрузить фотографию в любом меню и отправить всем пользователям бота\n\n'
            'Есть возможность оповестить всех пользоватлей текстовым сообщением. Для этого отправьте текст с ! в начале'
            'Пример:'
            '_!Привет всем пользоватлеям бота_'

            'Также вы можете изменить постоянное расписание загрузив таблицу в формате .xlsx сюда.\n\n',
            reply_markup=markup, parse_mode='Markdown')


def distributor(update, context):
    ini = update.message.text
    if ini == 'Я учитель':
        teacher_selection_menu(update, context)
    elif is_student(update, context):
        students(update, context)
    elif is_teacher(update, context):
        teachers(update, context)
    elif is_weekday(update, context):
        day = 0
        preprinting(update, context, day)
    elif ini == 'Сегодня':
        day = datetime.datetime.today().isoweekday()
        preprinting(update, context, day)
    elif ini == 'Завтра':
        day = datetime.datetime.today().isoweekday() + 1
        preprinting(update, context, day)

    # admin`s commands
    elif is_the_password_correct(update.message.text):
        add_to_admins(update, context)
    if is_admin(update, context):
        if ini == 'Изменить постоянное расписание':
            from_table_to_base(update, context)
        elif ini == 'Скачать расписание':
            send_table_to_admin(update, context)
            # from_base_to_table(update, context)
        elif ini == 'Нет':
            weekday_selection_menu(update, context)
        elif ini == 'Да, отправить фото':
            send_to_all_users(update, context, 0)
        elif ini == 'Да, отправить текст':
            send_to_all_users(update, context, 1)
        elif ini[0] == '!':
            confirm_to_send_text(update, context, ini)


def main():
    updater = Updater(token='884658566:AAG5l3pY4CacvQamPZBAJhF25NjUyQHnp4k', use_context=True)

    # get the dispatcher to register handlers (обработчики)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', class_selection_menu))
    dp.add_handler(CommandHandler('edit', editing))

    dp.add_handler(MessageHandler(filters=Filters.text, callback=distributor))
    dp.add_handler(MessageHandler(filters=Filters.photo, callback=download_photo))
    dp.add_handler(MessageHandler(filters=Filters.document, callback=download_document))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
