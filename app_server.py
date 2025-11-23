import socket
import threading
import json
import requests
import subprocess
import urllib.parse

PORT = 5000
HOST = '0.0.0.0'

def format_size(size_bytes):
    try:
        size = float(size_bytes)
        gb = size / (1024 * 1024 * 1024)
        return f"{gb:.2f} GB"
    except (ValueError, TypeError):
        return "N/A"

def search_torrents(query):
    try:
        url = f"https://apibay.org/q.php?q={urllib.parse.quote(query)}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        results = response.json()

        # Take top 10
        top_10 = results[:10]

        # Format for client
        formatted_results = []
        for item in top_10:
            formatted_item = {
                "id": item.get("id"),
                "name": item.get("name"),
                "info_hash": item.get("info_hash"),
                "size_bytes": item.get("size"),
                "size_formatted": format_size(item.get("size")),
                "seeders": item.get("seeders"),
                "leechers": item.get("leechers")
            }
            formatted_results.append(formatted_item)

        return json.dumps(formatted_results)
    except Exception as e:
        return json.dumps({"error": str(e)})

def start_download(info_hash, name):
    try:
        # Construct magnet link
        magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={urllib.parse.quote(name)}"

        # Try qBittorrent
        # Check if qbittorrent or qbittorrent-nox is available
        cmd = None
        if subprocess.run(["which", "qbittorrent"], stdout=subprocess.DEVNULL).returncode == 0:
            cmd = ["qbittorrent", "--skip-dialog=true", magnet]
        elif subprocess.run(["which", "qbittorrent-nox"], stdout=subprocess.DEVNULL).returncode == 0:
            cmd = ["qbittorrent-nox", "--skip-dialog=true", magnet]

        if cmd:
            subprocess.Popen(cmd)
            return "Download started"
        else:
            return "Error: qBittorrent not found"
    except Exception as e:
        return f"Error starting download: {str(e)}"

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            command_line = data.decode('utf-8').strip()
            print(f"Received: {command_line}")

            if command_line == "ping":
                response = "pong"
            elif command_line.startswith("search "):
                query = command_line[7:]
                response = search_torrents(query)
            elif command_line.startswith("download "):
                # Expecting "download <info_hash> <name>" or just info_hash
                parts = command_line.split(" ", 2)
                if len(parts) >= 2:
                    info_hash = parts[1]
                    name = parts[2] if len(parts) > 2 else "download"
                    response = start_download(info_hash, name)
                else:
                    response = "Invalid download command"
            else:
                response = "Unknown command"

            # Send response followed by newline
            conn.sendall((response + "\n").encode('utf-8'))

            # Close connection after one request as per current Android app logic
            # (Android app creates new socket for each request)
            break
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

if __name__ == "__main__":
    main()
