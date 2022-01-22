import sqlite3 as db
from sqlite3 import Error as Err

def connect(path):
    connection = None
    try:
        connection = db.connect(path)
    except Err as e:
        print("Connecting to database failed.",e,sep="\n")
    return connection

def execute(connection, query, objects=()): # write only commands, output supressed
    cursor = connection.cursor()
    try:
        cursor.execute(query, objects)
        connection.commit()
    except Err as e:
        print("Error while running query: ",query,"\n",e)
        return False
    return True

def execute_read(connection, query, objects=()):
    cursor = connection.cursor()
    try:
        cursor.execute(query, objects)
        return cursor.fetchall()
    except Err as e:
        print("Error while running query: ",query,"\n",e)
        return None

if __name__ == '__main__':
    print("Dont run db.py directly")
    print("To execute program run ./main.py")
