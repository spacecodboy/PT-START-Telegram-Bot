import logging, re, paramiko, os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv, find_dotenv
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import postgres_db
from datetime import datetime

find = find_dotenv()
load_dotenv() # Подключение модуля dotenv

TOKEN = os.getenv('TOKEN') # Токен бота

logging.basicConfig( # Подключаем логирование
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


handler = RotatingFileHandler('logfile.txt', maxBytes=5000000, backupCount=3) # Настройка максимального размера файла логирования и максимального количества данных файлов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)


def error_handler(update, context): # Обработчик исключений
    logger.error(f"Ошибка в обработчике {update}: {context.error}")

def connectToLinux(request): # Подключение к Linux
    host = os.getenv('RM_HOST')
    port = os.getenv('RM_PORT')
    username = os.getenv('RM_USER')
    password = os.getenv('RM_PASSWORD')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, port=port)
    stdin, stdout, stderr = client.exec_command(request)
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    return data

def connectToPostgresLogs(): # Подключение к серевру БД
    host = os.getenv('DB_LOG_HOST')
    port = os.getenv('DB_LOG_PORT')
    username = os.getenv('DB_LOG_USER')
    password = os.getenv('DB_LOG_PASSWORD')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, port=port)

    sftp_client = client.open_sftp()
    remote_file_path = '/var/log/postgresql/postgresql-15-main.log'  # Путь к файлу логов

    replication_logs = [] # Поиск логов репликации
    with sftp_client.open(remote_file_path, 'r') as remote_file:
        for line in remote_file:
            if "replication" in line:
                replication_logs.append(line)
                if len(replication_logs) > 10: # Вывод последних 10 записей
                    replication_logs.pop(0)

    # Отправка накопленных сообщений в Telegram
    data = ''
    for log_entry in replication_logs:
        data += f'{log_entry}\n'
    
    sftp_client.close()
    client.close()

    return data


def checkValidEmail(email): # Проверка на - и _ в начале адреса или домена
    addr = email.split('@')[0]
    if addr.startswith('-') or addr.endswith('-') or addr.startswith('_'):
            return False

    domain = email.split('@')[1]
    for subdomain in domain.split('.'):
        if subdomain.startswith('-') or subdomain.endswith('-'):
            return False

    return True

def start(update: Update, context):
    user = update.effective_user
    username = user.username or user.first_name
    with open("telegram_users.txt", "a") as file:
        file.write(f"{username}\n")
    update.message.reply_text(f'Привет {user.full_name}')
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /start.")


def helpCommand(update: Update, context):
    help_text = (
        "Список доступных команд:\n"
        "/start - Приветственное сообщение\n"
        "/help - Список всех команд\n"
        "/find_email - Поиск email-адресов в тексте\n"
        "/find_phone_number - Поиск телефонных номеров в тексте\n"
        "/verufy_password - Проверка пароля на сложность\n"
        "/get_release - Информация о версии Linux\n"
        "/get_uname - Архитектура процессора, имя хоста и версия ядра\n"
        "/get_uptime - Время работы системы\n"
        "/get_df - Состояние файловой системы\n"
        "/get_free - Состояние оперативной памяти\n"
        "/get_mpstat - Сбор информации о производительности системы\n"
        "/get_w - Сбор информации о работающих в данной системе пользователях\n"
        "/get_auths - Последние 10 входов в систему\n"
        "/get_critical - Последние 5 критических события\n"
        "/get_ps - Информация о запущенных процессах\n"
        "/get_ss - Информация об используемых портах\n"
        "/get_apt_list - Информация об установленных пакетах\n"
        "/get_services - Вывести список запущенных сервисов\n"
    )
    update.message.reply_text(help_text)
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /help.")


def findEmailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска email. Найденные emails будут записаны в базу данных.')
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /find_email.")
    return 'findEmail'


def findEmail (update: Update, context):
    user_input = update.message.text # Получаем текст, содержащий(или нет) email

    emailRegex = re.compile(r'[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    emailsList = emailRegex.findall(user_input) # Ищем emails

    if not emailsList: # Обрабатываем случай, когда emails нет
        update.message.reply_text('Email не найдены')
        return # Завершаем выполнение функции

    emails = '' # Создаем строку, в которую будем записывать emails
    for i in range(len(emailsList)):
        if checkValidEmail(emailsList[i]):
            emails += f'{i+1}. {emailsList[i]}\n' # Записываем очередной email
            result = postgres_db.insertEmails(emailsList[i])

    update.message.reply_text(emails) # Отправляем сообщение пользователю
    if result == None:
            update.message.reply_text('Данные успешно записаны')
    else:
        update.message.reply_text(result)
    return ConversationHandler.END # Завершаем работу обработчика диалога


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров. Найденные номера будут записаны в базу данных.')
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /find_phone_number.")
    return 'findPhoneNumbers'


def findPhoneNumbers (update: Update, context):
    user_input = update.message.text # Получаем текст, содержащий(или нет) номера телефонов

    phoneNumRegex = re.compile(r'(\+?7|8)([\- ]?)(\(?\d{3}\)?[\- ]?)(\d{3}[\- ]?)(\d{2}[\- ]?)(\d{2}[\- ]?)')

    phoneNumberList = phoneNumRegex.findall(user_input) # Ищем номера телефонов

    if not phoneNumberList: # Обрабатываем случай, когда номеров телефонов нет
        update.message.reply_text('Телефонные номера не найдены')
        return # Завершаем выполнение функции

    phoneNumbers = '' # Создаем строку, в которую будем записывать номера телефонов
    for i in range(len(phoneNumberList)):
        unpckPhoneNumber = ''
        for j in range(len(phoneNumberList[i])): # Распаковка кортежей для корректного вывода
            unpckPhoneNumber += phoneNumberList[i][j]
        phoneNumbers += f'{i+1}. {unpckPhoneNumber}\n' # Записываем очередной номер
        result = postgres_db.insertPhoneNumbers(unpckPhoneNumber)

    update.message.reply_text(phoneNumbers) # Отправляем сообщение пользователю
    if result == None:
            update.message.reply_text('Данные успешно записаны')
    else:
        update.message.reply_text(result)
    return ConversationHandler.END # Завершаем работу обработчика диалога


def passwdChekerCommand(update: Update, context):
    update.message.reply_text('Введите пароль для его проверки: ')
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /verify_password.")
    return 'passwdCheker'


def passwdCheker (update: Update, context):
    user_input = update.message.text # получаем пароль от пользователя

    passwdRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!@#$%^&*()]).{8,}$')

    if passwdRegex.match(user_input): # Проверка пароля
        update.message.reply_text(f'Пароль {user_input} сложный')
    else:
        update.message.reply_text(f'Пароль {user_input} простой')
    return ConversationHandler.END # Завершаем работу обработчика диалога

# Сбор информации о системе
def getRelease(update: Update, context):
    update.message.reply_text(connectToLinux('cat /etc/os-release'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_release.")

def getUname(update: Update, context):
    update.message.reply_text(connectToLinux('uname -m && hostname && uname -r'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_uname.")


def getUptime(update: Update, context):
    update.message.reply_text(connectToLinux('uptime'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_uptime.")


def getDf(update: Update, context):
    update.message.reply_text(connectToLinux('df -h'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_df.")


def getFree(update: Update, context):
    update.message.reply_text(connectToLinux('free -h'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_free.")


def getMpstat(update: Update, context):
    update.message.reply_text(connectToLinux('mpstat'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_mpstat.")


def getW(update: Update, context):
    update.message.reply_text(connectToLinux('w'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_w.")


def getAuths(update: Update, context):
    update.message.reply_text(connectToLinux('last -n 10'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_auths.")


def getCritical(update: Update, context):
    update.message.reply_text(connectToLinux('journalctl -p crit -n 5'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_critical.")


def getPs(update: Update, context):
    update.message.reply_text(connectToLinux('ps aux | head -n 30'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_ps.")


def getSs(update: Update, context):
    update.message.reply_text(connectToLinux('ss -tuln'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_ss.")


def getAptListCommand(update: Update, context):
    update.message.reply_text('Введите название пакета, для которого требуется вывести информацию. Для вывода информации о всех пакетах введите: all ')
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_apt_list.")
    return 'getAptList'


def getAptList (update: Update, context):
    user_input = update.message.text

    if user_input == 'all': # Вывод первых 50 пакетов
        update.message.reply_text(connectToLinux("dpkg -l | grep '^ii' | awk '{print $2}' | head -n 50"))
    else: # Вывод конкретного пакета
        apt_list = connectToLinux(f'dpkg -l | grep {user_input}')
        if apt_list != '':
            update.message.reply_text(connectToLinux(f'dpkg -l | grep {user_input}'))
        else: # Если пакет не найден
            update.message.reply_text('Данный пакет не найден.')
    return ConversationHandler.END # Завершаем работу обработчика диалога

def getServices(update: Update, context):
    update.message.reply_text(connectToLinux('systemctl list-units --type=service --state=running'))
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /services.")

def getReplLogs(update: Update, context):
    update.message.reply_text(connectToPostgresLogs())
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_repl_logs.")

def getEmails(update: Update, context):
    update.message.reply_text(postgres_db.selectEmails())
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_emails.")

def getPhoneNumbers(update: Update, context):
    update.message.reply_text(postgres_db.selectPhoneNumbers())
    logger.info(f"Пользователь {update.message.from_user.username} запустил команду /get_phone_numbers.")

def echo(update: Update, context):
    update.message.reply_text(update.message.text)

# def unknownCommand(update: Update, context) -> None:
#     # Отправляем сообщение о неизвестной команде
#     update.message.reply_text("Неизвестная команда. Используйте /help для получения списка доступных команд.")


def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Диспетчер для обработки исключений
    dp.add_error_handler(error_handler)

    # Обработчики диалога
    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
        },
        fallbacks=[]
    )

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailCommand)],
        states={
            'findEmail': [MessageHandler(Filters.text & ~Filters.command, findEmail)],
        },
        fallbacks=[]
    )

    convHandlerPasswdChecker = ConversationHandler(
        entry_points=[CommandHandler('verify_password', passwdChekerCommand)],
        states={
            'passwdCheker': [MessageHandler(Filters.text & ~Filters.command, passwdCheker)],
        },
        fallbacks=[]
    )

    convHandlerGetAppList = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', getAptListCommand)],
        states={
            'getAptList': [MessageHandler(Filters.text & ~Filters.command, getAptList)],
        },
        fallbacks=[]
    )

        # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmails)
    dp.add_handler(convHandlerPasswdChecker)
    dp.add_handler(CommandHandler("get_release", getRelease))
    dp.add_handler(CommandHandler("get_uname", getUname))
    dp.add_handler(CommandHandler("get_uptime", getUptime))
    dp.add_handler(CommandHandler("get_df", getDf))
    dp.add_handler(CommandHandler("get_free", getFree))
    dp.add_handler(CommandHandler("get_mpstat", getMpstat))
    dp.add_handler(CommandHandler("get_w", getW))
    dp.add_handler(CommandHandler("get_auths", getAuths))
    dp.add_handler(CommandHandler("get_critical", getCritical))
    dp.add_handler(CommandHandler("get_ps", getPs))
    dp.add_handler(CommandHandler("get_ss", getSs))
    dp.add_handler(convHandlerGetAppList)
    dp.add_handler(CommandHandler("get_services", getServices))
    dp.add_handler(CommandHandler("get_repl_logs", getReplLogs))
    dp.add_handler(CommandHandler("get_emails", getEmails))
    dp.add_handler(CommandHandler("get_phone_numbers", getPhoneNumbers))
    # dp.add_handler(MessageHandler(Filters.command, unknownCommand))

        # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

        # Запускаем бота
    updater.start_polling()

        # Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
