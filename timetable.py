import logging
import telegram
import sqlite3
import datetime
import hashlib

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
    con= sqlite3.connect('BOTSBASE.db')
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
        if update.message.text == a[i]:
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


# connect user(chat_id) and class in table "Users"
def students(update, context):
    user = str(update.message.chat_id)
    cur_class = str(class_to_id(update.message.text))

    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()

    isreg = cur.execute(f'select class_ from Users where chat_id == {user};').fetchone()
    if (isreg == None):
        cur.execute(f'INSERT INTO main.Users(chat_id, class_) VALUES ({user}, {cur_class});')
    else:
        cur.execute(f'UPDATE Users SET class_ = {cur_class} WHERE chat_id == {user}')

    con.commit()
    con.close()

    weekday_selection_menu(update, context)


def printing_for_students(update, context):
    con = sqlite3.connect('BOTSBASE.db')
    cur = con.cursor()
    # get id of weekday
    weekday_id = cur.execute(
        f'select id from Weekdays where weekday == "{update.message.text}";').fetchone()

    user = update.message.chat_id
    class_ = cur.execute(f'select class_ from Users WHERE chat_id == {user}').fetchone()
    # get timetable for this weekday and class
    timetable = cur.execute(
        f'select lesson, cab, lesson_number from main_timetable where weekday == {weekday_id[0]} and class_ == {class_[0]} order by lesson_number;').fetchall()

    keyboard = ""

    i = 0
    les_num = 1
    while i < len(timetable):
        keyboard += f"{les_num})"
        lesson_name = cur.execute(
            f'select lesson from Lessons where id=={timetable[i][0]};').fetchone()
        if len(timetable) - i > 1:
            if timetable[i][2] == timetable[i + 1][2]:
                if timetable[i][0] != timetable[i + 1][0]:
                    lesson_name2 = cur.execute(
                        f'select lesson from Lessons where id=={timetable[i + 1][0]}').fetchone()
                    keyboard += f"{lesson_name[0]} ({timetable[i][1]}) / {lesson_name2[0]} ({timetable[i + 1][1]})\n"
                    print(lesson_name)
                    print(lesson_name2)
                else:
                    keyboard += f"{lesson_name[0]} ({timetable[i][1]}) / ({timetable[i + 1][1]})\n"
                i += 2
                les_num += 1
                continue

        keyboard += f"{lesson_name[0]} ({timetable[i][1]})\n"
        i += 1
        les_num += 1

    con.close()
    update.message.reply_text(keyboard)


def distributor(update, context):
    # calling other functions go by text from human
    if update.message.text == 'Я учитель':
        teacher_selection_menu(update, context)
    if is_student(update, context):
        students(update, context)
    if is_teacher(update, context):
        students(update, context)
    if is_weekday(update, context):
        printing_for_students(update, context)


def main():
    updater = Updater(token='TOKEN', use_context=True)

    # get the dispatcher to register handlers (обработчики)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', class_selection_menu))
    dp.add_handler(CommandHandler('edit_timetable', head_teacher_loggining))

    dp.add_handler(MessageHandler(filters=Filters.text, callback=distributor))
    updater.start_polling()
    updater.idle()


# not using
def is_the_password_correct(the_password):  # может использовать много памяти
    return hashlib.pbkdf2_hmac('sha256', the_password.encode('UTF-8'), b'PTS', 50) == #


def head_teacher_loggining(update, context):
    update.message.reply_text('Меню редактирования расписания.\nДля внесения изменений введите пароль.\n'
                              'Попали сюда случайно? /start')

    if is_the_password_correct(update.message.text):
        update.message.reply_text('Успешно!!!')
        # smth
    else:
        update.message.reply_text('НЕВЕРНЫЙ ПАРОЛЬ.\nПопробуйте еще раз')


# not using

if __name__ == '__main__':
    main()
