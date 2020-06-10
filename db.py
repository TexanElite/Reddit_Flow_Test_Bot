import sqlite3 as sql
import sys

class Entry:
    def __init__(self, id, url, username, code):
        self.id = id
        self.url = url
        self.username = username
        self.code = code


def initialize_database():
    try:
        con = sql.connect('interviews.db')
        cur = con.cursor()
        cur.execute("SELECT SQLITE_VERSION()")
        data = cur.fetchone()
        print(f'SQLite version: {data}')

        # Check if the table exists. If it doesn't, make a table

        cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='interviews'")
        data = cur.fetchone()
        if data[0] == 0:
            cur.execute("CREATE TABLE interviews (id TEXT PRIMARY KEY, url TEXT NOT NULL, username TEXT NOT NULL, code TEXT NOT NULL)")
            print('Table interviews doesn\'t exist: creating new table')
        
        con.commit()

        return 0
    except sql.Error as e:
        print(f'Error: {e.args[0]}')
        return 1

def get_entry(url):
    try:
        con = sql.connect('interviews.db')
        cur = con.cursor()
        command = "select * from interviews where url=?"
        cur.execute(command, (url,))
        response = cur.fetchone()
        if response == None:
            return None
        return Entry(response[0], response[1], response[2], response[3])
    except sql.Error as e:
        print(f'Error while retrieving: {e.args[0]}')
        return None

def get_all():
    try:
        con = sql.connect('interviews.db')
        cur = con.cursor()
        command = "select * from interviews"
        cur.execute(command)
        response = cur.fetchall()
        if response == None:
            return None
        entries = []
        for i in range(len(response)):
            entries.append(Entry(response[i][0], response[i][1], response[i][2], response[i][3]))
        return entries
    except sql.Error as e:
        print(f'Error while retrieving: {e.args[0]}')
        return None

def add_entry(id, url, username, code):
    try:
        con = sql.connect('interviews.db')
        cur = con.cursor()
        command = "INSERT INTO interviews VALUES (?,?,?,?)"
        cur.execute(command, (id, url, username, code))
        con.commit()
    except sql.Error as e:
        print(f'Error while inserting: {e.args[0]}')

def update_code(id, code):
    try:
        con = sql.connect('interviews.db')
        cur = con.cursor()
        command = "UPDATE interviews SET code=? WHERE id=?"
        cur.execute(command, (code, id))
        con.commit()
    except sql.Error as e:
        print(f'Error while updating: {e.args[0]}')

def remove_entry(id):
    try:
        con = sql.connect('interviews.db')
        cur = con.cursor()
        command = "DELETE FROM interviews WHERE id=?"
        cur.execute(command, (id,))
        con.commit()
        con.close()
    except sql.Error as e:
        print(f'Error while removing: {e.args[0]}')
