import socket
import threading
import json
import requests
import subprocess
import urllib.parse
import subprocess

PORT = 5000
HOST = '0.0.0.0'
QBT_PORT = 8080  # Default qBittorrent WebUI port
QBT_USER = 'admin'
QBT_PASS = 'QBcwkmy8s!'

def get_qbt_list():
    try:
        session = requests.Session()
        login_url = f"http://localhost:{QBT_PORT}/api/v2/auth/login"
        data = {'username': QBT_USER, 'password': QBT_PASS}
        resp = session.post(login_url, data=data)
        resp.raise_for_status()
        if resp.text != "Ok.":
            return {"error": "Failed to authenticate with qBittorrent"}

        torrents_url = f"http://localhost:{QBT_PORT}/api/v2/torrents/info"
        resp = session.get(torrents_url)
        resp.raise_for_status()
        torrents = resp.json()

        formatted_torrents = []
        for t in torrents:
            formatted_torrents.append({
                "hash": t.get("hash"),
                "name": t.get("name"),
                "size_bytes": t.get("size"),
                "size_formatted": format_size(t.get("size")),
                "progress": t.get("progress"),
                "state": t.get("state"),
                "seeds": t.get("num_seeds"),
                "leechers": t.get("num_leechs"),
                "download_speed": t.get("dlspeed"),
                "upload_speed": t.get("upspeed")
            })

        return json.dumps(formatted_torrents)
    except Exception as e:
        return json.dumps({"error": str(e)})

def delete_torrent(info_hash):
    try:
        session = requests.Session()
        login_url = f"http://localhost:{QBT_PORT}/api/v2/auth/login"
        data = {'username': QBT_USER, 'password': QBT_PASS}
        resp = session.post(login_url, data=data)
        resp.raise_for_status()

        delete_url = f"http://localhost:{QBT_PORT}/api/v2/torrents/delete"
        # deleteFiles=true to delete content too
        data = {'hashes': info_hash, 'deleteFiles': 'true'}
        resp = session.post(delete_url, data=data)
        resp.raise_for_status()

        return "Torrent deleted"
    except Exception as e:
        return f"Error deleting torrent: {str(e)}"

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
        save_path = os.path.expanduser("~/Videos/2. Films")  # Expand user's home directory
        if subprocess.run(["which", "qbittorrent"], stdout=subprocess.DEVNULL).returncode == 0:
            cmd = ["qbittorrent", "--skip-dialog=true", f"--save-path={save_path}", magnet]
        elif subprocess.run(["which", "qbittorrent-nox"], stdout=subprocess.DEVNULL).returncode == 0:
            cmd = ["qbittorrent-nox", "--skip-dialog=true", f"--save-path={save_path}", magnet]

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
            elif command_line == "list_torrents":
                response = get_qbt_list()
            elif command_line.startswith("delete_torrent "):
                info_hash = command_line[15:]
                response = delete_torrent(info_hash)
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

def connect_nordvpn():
    try:
        # Connect to NordVPN
        print("Connecting to NordVPN...")
        subprocess.run(["nordvpn", "connect"], check=True)
        print("NordVPN connected successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error connecting to NordVPN: {e}")
        return False
    return True

def check_nordvpn_status():
    try:
        # Check NordVPN connection status
        result = subprocess.run(["nordvpn", "status"], stdout=subprocess.PIPE, text=True)
        if "Connected" in result.stdout:
            print("NordVPN is connected.")
            return True
        else:
            print("NordVPN is not connected.")
            return False
    except Exception as e:
        print(f"Error checking NordVPN status: {e}")
        return False

def main():
    # Connect to NordVPN
    if not connect_nordvpn():
        print("Failed to connect to NordVPN. Exiting...")
        return

    # Verify NordVPN connection
    if not check_nordvpn_status():
        print("NordVPN is not connected. Exiting...")
        return

    # Start the server
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
