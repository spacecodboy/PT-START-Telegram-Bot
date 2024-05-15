import logging
import psycopg2
from psycopg2 import Error
import os
from dotenv import load_dotenv, find_dotenv

logging.basicConfig(
    filename='app.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, encoding="utf-8"
)


find_dotenv()
load_dotenv()


def createConnection(db_name, db_user, db_password, db_host, db_port):
    connection = None
    try:
        connection = psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        logging.info("Подключение к базе данных PostgreSQL прошло успешно")
    except (Exception, Error) as error:
        logging.error(f"Произошла ошибка при работе с PostgreSQL: '{error}'")
    return connection

connection = None
while connection == None:
    logging.error("Выполняется подключение к базе данных.")
    connection = createConnection(
        os.getenv('DB_DATABASE'), os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), os.getenv('DB_HOST'), os.getenv('DB_PORT')
    break;
)

def executeReadQuery(connection, query):
    cursor = connection.cursor()
    result = None
    cursor.execute(query)
    result = cursor.fetchall()
    return result

def executeInsertQuery(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()

def selectEmails():
    try:
        response = executeReadQuery(connection, f'''SELECT * FROM emails;''')
        answer = ''
        for i in range(len(response)):
            answer += f'{i+1}. {response[i][1]}\n'
    except (Exception, Error) as error:
        logging.error(f"Произошла ошибка при выводе данных: '{error}'")
        return 'Произошла ошибка при выводе данных.'
    return answer

def selectPhoneNumbers():
    try:
        response = executeReadQuery(connection, f'''SELECT * FROM phone_numbers;''')
        answer = ''
        for i in range(len(response)):
            answer += f'{i+1}. {response[i][1]}\n'
    except (Exception, Error) as error:
        logging.error(f"Произошла ошибка при выводе данных: '{error}'")
        return 'Произошла ошибка при выводе данных.'
    return answer

def insertEmails(data):
    try:
        executeInsertQuery(connection, f'''INSERT INTO emails (email) VALUES ('{data}');''')
    except (Exception, Error) as error:
        logging.error(f"Произошла ошибка при записи данных: '{error}'")
        return 'Произошла ошибка при записи данных.'


def insertPhoneNumbers(data):
    try:
        executeInsertQuery(connection, f'''INSERT INTO phone_numbers (phone_number) VALUES ('{data}');''')
    except (Exception, Error) as error:
        logging.error(f"Произошла ошибка при записи данных: '{error}'")
        return 'Произошла ошибка при записи данных.'