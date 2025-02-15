import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import os

class DatabaseManager:
    def __init__(self, db_path="data/app.db"):
        """Initialize database connection and create tables if they don't exist."""
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Create a database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            self.create_tables()
            return True
        except sqlite3.Error as e:
            st.error(f"Database connection error: {e}")
            return False
            
    def disconnect(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            
    def create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_data (id)
            )
        ''')
        self.conn.commit()
        
    def add_user(self, username, email):
        """Add a new user to the database."""
        try:
            self.cursor.execute(
                "INSERT INTO user_data (username, email) VALUES (?, ?)",
                (username, email)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            st.warning("Email already exists!")
            return False
        except sqlite3.Error as e:
            st.error(f"Error adding user: {e}")
            return False
            
    def add_entry(self, user_id, content):
        """Add a new entry for a user."""
        try:
            self.cursor.execute(
                "INSERT INTO entries (user_id, content) VALUES (?, ?)",
                (user_id, content)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Error adding entry: {e}")
            return False
            
    def get_user_entries(self, user_id):
        """Get all entries for a specific user."""
        try:
            query = """
                SELECT e.id, e.content, e.created_at 
                FROM entries e
                WHERE e.user_id = ?
                ORDER BY e.created_at DESC
            """
            df = pd.read_sql_query(query, self.conn, params=(user_id,))
            return df
        except sqlite3.Error as e:
            st.error(f"Error retrieving entries: {e}")
            return pd.DataFrame()
            
    def get_all_users(self):
        """Get all users from the database."""
        try:
            query = "SELECT * FROM user_data ORDER BY created_at DESC"
            df = pd.read_sql_query(query, self.conn)
            return df
        except sqlite3.Error as e:
            st.error(f"Error retrieving users: {e}")
            return pd.DataFrame()

# Example Streamlit app implementation
def main():
    st.title("Persistent Data Storage Demo")
    
    # Initialize database
    db = DatabaseManager()
    if not db.connect():
        st.error("Failed to connect to database")
        return
        
    # Sidebar for user management
    with st.sidebar:
        st.header("Add New User")
        username = st.text_input("Username")
        email = st.text_input("Email")
        if st.button("Add User"):
            if username and email:
                if db.add_user(username, email):
                    st.success("User added successfully!")
                    
    # Main content area
    users_df = db.get_all_users()
    if not users_df.empty:
        st.header("Users")
        st.dataframe(users_df)
        
        # Add entry for selected user
        selected_user = st.selectbox(
            "Select User",
            options=users_df['id'].tolist(),
            format_func=lambda x: users_df[users_df['id'] == x]['username'].iloc[0]
        )
        
        content = st.text_area("New Entry")
        if st.button("Add Entry"):
            if content:
                if db.add_entry(selected_user, content):
                    st.success("Entry added successfully!")
                    
        # Display user entries
        entries_df = db.get_user_entries(selected_user)
        if not entries_df.empty:
            st.header("User Entries")
            st.dataframe(entries_df)
            
    # Close database connection
    db.disconnect()

if __name__ == "__main__":
    main()
