import sqlite3

class SQLiteDB:
    @staticmethod
    def fetch_tile_data(media_path):
        query = f"SELECT title, thumbnail FROM media WHERE file_path = '{media_path}'"
        results = SQLiteDB.query(query)
        return results[0] if results else (None, None)

    @staticmethod
    def query(query):
        conn = sqlite3.connect('media_metadata.db')
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return results