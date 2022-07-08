import mysql.connector
from mysql.connector import Error
import requests
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
from prettytable import PrettyTable

fopen = open("passwords.txt", "r")
lines = fopen.readlines()
rootpass = lines[0][:-1]
mailpass = lines[1][:-1]


def listing(cursor):

    """Functie de afisare a site-urilor din baza de date"""

    try:
        sql_select_query = """select * from crawling"""
        cursor.execute(sql_select_query)
        records = cursor.fetchall()
        mytable = PrettyTable()
        mytable.field_names = ["ID", "Website Name", "Hash"]
        for row in records:
            mytable.add_row([row[0], row[1], row[2]])
        print(mytable)
        #   print(f"Id:{row[0]} / Name:{row[1]} / Modified hash:{row[2]}")
    except mysql.connector.Error as error:
        print("Failed to get record from MySQL table: {}".format(error))


def insert(cursor, connection, args):

    """Functie de inserare a unui site in baza de date.
    Funtia trebuie sa fie de forma: id url hash"""

    if len(args) < 3:
        print("Wrong number of arguments!")
    if args[1][0:4] != "http":
        print("ERROR: Give me a website!")
    elif len(args) != 3:
        print("Wrong number of arguments! Give: id,url,date!")
    else:
        try:
            sql_insert_query = """insert into crawling values(%s, %s, %s)"""
            data = (args[0], args[1], args[2])
            cursor.execute(sql_insert_query, data)
            connection.commit()
            print("Record inserted successfully!")
        except mysql.connector.Error as error:
            print("Failed to insert into MySQL table {}".format(error))


def add(cursor, connection, url):

    """Functie de inserare a unui site in baza de date.
        Funtia poate sa aiba doar un parametru: url"""

    if url[0:4] != "http":
        print("ERROR:Give me a website!")
    else:
        try:
            sql_select_query = """select * from crawling where id=(select max(id) from crawling)"""
            sql_insert_query = """insert into crawling values(%s, %s, %s)"""
            cursor.execute(sql_select_query)
            records = cursor.fetchone()
            new_id = int(records[0]) + 1
            hash = ""
            data = (new_id, url, hash)
            cursor.execute(sql_insert_query, data)
            connection.commit()
            print("Record inserted successfully!")
        except mysql.connector.Error as error:
            print("Failed to insert into MySQL table {}".format(error))


def delete(cursor, connection, id):

    """Functie care sterge o inregistrare din baza de date"""

    try:
        sql_delete_query = """delete from crawling where id = %s"""
        data = id
        cursor.execute(sql_delete_query, (data,))
        connection.commit()
        print("Record deleted successfully!")
    except mysql.connector.Error as error:
        print("Failed to delete from MySQL table {}".format(error))


def update(cursor, connection, id, modified):

    """Functie de actualizare a unei inregistrari. Aceasta modifica doar hash-ul"""

    try:
        sql_update_query = """update crawling set modified = %s where id = %s"""
        data = (modified, id)
        cursor.execute(sql_update_query, data)
        connection.commit()
        print("Record updated successfully!")
    except mysql.connector.Error as error:
        print("Failed to update record to database: {}".format(error))


def email(modified):

    """Functia care creeaza un mail si il trimite actualizarea atunci cand are loc o modificare intr-un site"""

    try:
        email_from = "pythonprojectb1@gmail.com"
        from_pass = mailpass
        email_to = "tudorstelaru@gmail.com"
        msg = MIMEMultipart()
        msg.attach(MIMEText(
            f"The URL you've been watching has been modified!\n The latest modification happened on: {modified}",
            'plain'))
        msg['Subject'] = 'Site Update Notification'
        msg['From'] = email_from
        msg['To'] = email_to
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(email_from, from_pass)
        text = msg.as_string()
        server.sendmail(email_from, email_to, text)
        server.quit()
        print("Email sent!")
    except Exception as error:
        print("Error: {}!\n\n".format(error))


def check(cursor, connection, url):

    """Functie care verifica daca a avut loc vreo modificare intr-o pagina din baza de date.
    Daca nu exista site-ul va transmite un mesaj"""

    if url[0:4] != "http":
        print("ERROR:Give me a website!")
    else:
        try:
            sql_select_query = """select * from crawling where name = %s"""
            data = url
            cursor.execute(sql_select_query, (data,))
            row = cursor.fetchone()
            if row == None:
                print("Website does not exist in the database!")
            else:
                try:
                    r = requests.get(url)
                    content = r.text
                    hash_content = hashlib.md5(content.encode('utf-8')).hexdigest()
                    if row[2] != hash_content:
                        update(cursor, connection, row[0], hash_content)
                        email(row[1])
                except Exception as error:
                    print("Error: {}.".format(error))
        except mysql.connector.Error as error:
            print("Failed to get record from MySQL table: {}".format(error))


def connect():

    """Functie care face conectarea la baza de date. De asemenea verifica parametri din linia de comanda
    si apeleaza functiile respective comenzilor date. Daca datele din linia de comanda nu sunt corecte
    fiecare functie va transmise mesaje respective erorilor aparute"""

    try:
        connection = mysql.connector.connect(host='localhost',
                                             database='crawler',
                                             user='root',
                                             password=rootpass)
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print("You're connected to database: ", record)
            if sys.argv[1] == "list":
                listing(cursor)
            elif sys.argv[1] == "insert":
                insert(cursor, connection, sys.argv[2:])
            elif sys.argv[1] == "add":
                add(cursor, connection, sys.argv[2])
            elif sys.argv[1] == "delete":
                delete(cursor, connection, sys.argv[2])
            elif sys.argv[1] == "update":
                update(cursor, connection, sys.argv[2], sys.argv[3])
            else:
                check(cursor, connection, sys.argv[1])
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed!")


if __name__ == '__main__':
    connect()
