import sqlite3
import os

DATABASE_NAME = 'bot_data.db'

def create_connection(db_file=DATABASE_NAME):
    """Create a database connection to the SQLite database specified by db_file."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

def create_tables():
    """Create tables if they do not exist."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Users table now only stores the user_id
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY
                );
            ''')
            # store encrypted passwords
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    site_name TEXT NOT NULL,
                    encrypted_password BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );
            ''')
            conn.commit()
            print("Tables created or already exist.")
        except sqlite3.Error as e:
            print(e)
        finally:
            conn.close()

def add_user(user_id):
    """Adds a new user to the users table."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()
        finally:
            conn.close()

def save_password(user_id, site_name, encrypted_password):
    """Saves a new encrypted password for a user."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO passwords (user_id, site_name, encrypted_password) VALUES (?, ?, ?)",
                           (user_id, site_name, encrypted_password))
            conn.commit()
        finally:
            conn.close()

def get_passwords(user_id):
    """Retrieves all saved passwords for a user."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT site_name, encrypted_password FROM passwords WHERE user_id = ?", (user_id,))
            return cursor.fetchall()
        finally:
            conn.close()

def delete_password_from_db(user_id, site_name):
    """Deletes a password entry from the database for a given user and site name."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM passwords WHERE user_id = ? AND site_name = ?", (user_id, site_name))
            conn.commit()
        finally:
            conn.close()

def delete_all_passwords_from_db(user_id):
    """Deletes all password entries from the database for a given user."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM passwords WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()
