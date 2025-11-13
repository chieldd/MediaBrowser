import os
import re
import sys
import sqlite3
from tmdbv3api import TMDb, Movie, TV, Season, Episode

# Initialize TMDb
tmdb = TMDb()
tmdb.api_key = '3258abe1d2a38e9a04e340fbb18da435'  # Replace with your TMDb API key

VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.webm', '.avi', '.mov']
DB_PATH = os.path.join(os.path.dirname(__file__), 'media_metadata.db')
SHOWS_TABLE_SQL = '''CREATE TABLE IF NOT EXISTS shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder TEXT UNIQUE,
    title TEXT,
    poster TEXT
)'''

def parse_filename(filename):
    basename = os.path.basename(filename)
    name = os.path.splitext(basename)[0]
    # Try to match TV show pattern: "Show Name S01E02"
    tv_match = re.match(r'(.+)[ ._-]+S(\d{1,2})E(\d{1,2})', name, re.IGNORECASE)
    if tv_match:
        print("TV show detected.")
        show = tv_match.group(1).replace('.', ' ').replace('_', ' ').strip()
        season = int(tv_match.group(2))
        episode = int(tv_match.group(3))
        print(f"Detected TV Show: {show}, Season: {season}, Episode: {episode}")
        return {'type': 'tv', 'show': show, 'season': season, 'episode': episode}
    # Try to match movie pattern: "Movie Name.2020"
    movie_match = re.match(r'(.+)[ ._-]+(\d{4})$', name)
    if movie_match:
        print("Movie detected.")
        title = movie_match.group(1).replace('.', ' ').replace('_', ' ').strip()
        year = movie_match.group(2)
        return {'type': 'movie', 'title': title, 'year': year}
    # Fallback: treat as movie with no year
    return {'type': 'movie', 'title': name.replace('.', ' ').replace('_', ' ').strip(), 'year': None}

def get_movie_metadata(title, year=None):
    movie = Movie()
    query = title
    if year:
        query += f" y:{year}"  # Append year to the query
    results = movie.search(query)
    for result in results:
        if year and result.release_date and str(result.release_date).startswith(str(year)):
            return result
        elif not year:
            return result
    return None

def get_tv_metadata(show, season, episode):
    tv = TV()
    results = tv.search(show)
    
    # Ensure results is a list
    if not isinstance(results, list):
        print(f"Unexpected response from TMDb for '{show}': {results}")
        return None

    print(f"TV search results for '{show}': {[r.name for r in results]}")
    if not results:
        print("No TV show results found.")
        return None

    show_id = results[0].id
    try:
        print(f"Retrieving metadata for Show ID: {show_id}, Season: {season}, Episode: {episode}")
        season_data = Season().details(show_id, season)
        print("Episodes found in season:")
        for ep in season_data.episodes:
            print(f"  Episode {ep.episode_number}: {getattr(ep, 'name', '')}")
            if ep.episode_number == episode:
                return ep
        print("Episode not found in season data.")
        return None
    except Exception as e:
        print(f"Error retrieving episode metadata: {e}")
        return None

def print_metadata(metadata):
    if metadata is None:
        print("No metadata found.")
    elif hasattr(metadata, 'name'):
        print(f"Title: {metadata.name}")
        print(f"Release Date: {getattr(metadata, 'release_date', getattr(metadata, 'air_date', ''))}")
        print(f"Overview: {getattr(metadata, 'overview', '')}")
        print(f"TMDb ID: {getattr(metadata, 'id', '')}")
    elif hasattr(metadata, 'title'):
        print(f"Title: {metadata.title}")
        print(f"Release Date: {getattr(metadata, 'release_date', getattr(metadata, 'air_date', ''))}")
        print(f"Overview: {getattr(metadata, 'overview', '')}")
        print(f"TMDb ID: {getattr(metadata, 'id', '')}")
    else:
        print(f"Metadata is not a TMDb object: {metadata}")

def insert_metadata_to_db(conn, file_path, metadata):
    cursor = conn.cursor()
    # Check if the file has already been processed
    cursor.execute("SELECT id FROM media WHERE file_path = ?", (file_path,))
    if cursor.fetchone():
        print(f"Skipping {file_path}: Already processed.")
        return

    if metadata is None or isinstance(metadata, str):
        print(f"Skipping {file_path}: No valid metadata found.")
        return

    # Extract fields from TMDb metadata
    if hasattr(metadata, 'name'):  # TV episode
        title = metadata.name
        release_date = getattr(metadata, 'release_date', getattr(metadata, 'air_date', None))
        duration = getattr(metadata, 'runtime', None)
        description = getattr(metadata, 'overview', None)
        director = None
        genre = None
        rating = getattr(metadata, 'vote_average', None)
        resolution = None
        thumbnail = metadata.still_path and f"https://image.tmdb.org/t/p/w500{metadata.still_path}" or None
    else:  # Movie
        title = metadata.title
        release_date = getattr(metadata, 'release_date', None)
        duration = getattr(metadata, 'runtime', None)
        description = getattr(metadata, 'overview', None)
        director = None
        genre = ', '.join([g['name'] for g in getattr(metadata, 'genres', [])]) if hasattr(metadata, 'genres') else None
        rating = getattr(metadata, 'vote_average', None)
        resolution = None
        thumbnail = metadata.poster_path and f"https://image.tmdb.org/t/p/w500{metadata.poster_path}" or None

    cursor.execute('''
        INSERT OR REPLACE INTO media (
            file_path, title, release_date, duration, description, director, genre, rating, resolution, thumbnail
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (file_path, title, release_date, duration, description, director, genre, rating, resolution, thumbnail))
    conn.commit()

    if metadata is None or isinstance(metadata, str):
        print(f"Skipping {file_path}: No valid metadata found.")
        return
    cursor = conn.cursor()
    # Extract fields from TMDb metadata
    if hasattr(metadata, 'name'):  # TV episode
        title = metadata.name
        release_date = getattr(metadata, 'release_date', getattr(metadata, 'air_date', None))
        duration = getattr(metadata, 'runtime', None)
        description = getattr(metadata, 'overview', None)
        director = None
        genre = None
        rating = getattr(metadata, 'vote_average', None)
        resolution = None
        thumbnail = metadata.still_path and f"https://image.tmdb.org/t/p/w500{metadata.still_path}" or None
    else:  # Movie
        title = metadata.title
        release_date = getattr(metadata, 'release_date', None)
        duration = getattr(metadata, 'runtime', None)
        description = getattr(metadata, 'overview', None)
        director = None
        genre = ', '.join([g['name'] for g in getattr(metadata, 'genres', [])]) if hasattr(metadata, 'genres') else None
        rating = getattr(metadata, 'vote_average', None)
        resolution = None
        thumbnail = metadata.poster_path and f"https://image.tmdb.org/t/p/w500{metadata.poster_path}" or None
    cursor.execute('''
        INSERT OR REPLACE INTO media (
            file_path, title, release_date, duration, description, director, genre, rating, resolution, thumbnail
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (file_path, title, release_date, duration, description, director, genre, rating, resolution, thumbnail))
    conn.commit()

def insert_show_to_db(conn, folder, title, poster):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO shows (folder, title, poster)
        VALUES (?, ?, ?)
    ''', (folder, title, poster))
    conn.commit()

def find_all_video_files(root_dir):
    video_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if any(fname.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                video_files.append(os.path.join(dirpath, fname))
    return video_files

def ingest_shows(root_dir):
    root_dir = os.path.expanduser(root_dir)  # Expand '~' to the full path
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SHOWS_TABLE_SQL)
    tv = TV()
    for show_folder in os.listdir(root_dir):
        show_path = os.path.join(root_dir, show_folder)
        if os.path.isdir(show_path):
            results = tv.search(show_folder)
            if isinstance(results, list) and results:  # Ensure results is a list and not empty
                show_meta = results[0]
                poster = show_meta.poster_path and f"https://image.tmdb.org/t/p/w500{show_meta.poster_path}" or None
                insert_show_to_db(conn, show_folder, show_meta.name, poster)
    conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <media_root_dir>")
        root_dir = os.path.expanduser("~/Videos/2. Films")
        print(f"No directory provided. Using default: {root_dir}")
    else:
        root_dir = sys.argv[1]
    ingest_shows(root_dir)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE,
        title TEXT,
        release_date TEXT,
        duration INTEGER,
        description TEXT,
        director TEXT,
        genre TEXT,
        rating INTEGER,
        resolution TEXT,
        thumbnail TEXT
    )''')
    video_files = find_all_video_files(root_dir)
    print(f"Found {len(video_files)} video files.")
    for file_path in video_files:
        print(f"Processing: {file_path}")
        info = parse_filename(file_path)
        if info['type'] == 'movie':
            metadata = get_movie_metadata(info['title'], info['year'])
        else:
            metadata = get_tv_metadata(info['show'], info['season'], info['episode'])
        print_metadata(metadata)
        insert_metadata_to_db(conn, file_path, metadata)
    conn.close()

if __name__ == "__main__":
    main()