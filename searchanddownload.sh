#!/usr/bin/env bash

# Save path (modify as needed)
SAVE_PATH="$HOME/Videos/2. Films"

# Check for query
if [ -z "$1" ]; then
    echo "Usage: $0 <search query>"
    exit 1
fi

QUERY="$*"

echo "Searching for: $QUERY"
echo

#############################################
# Replace the block below with your own
# search command that outputs 2 lines:
#   NAME
#   MAGNET_LINK
#############################################

# Example placeholder search function.
# YOU must replace this with your own data-source command.
search_result=$(piratebay -j search "$QUERY")
# Expecting 2-line output
first_id=$(echo "$search_result" | jq -r '.[0].id')
echo "$first_id"
first_name=$(echo "$search_result" | jq -r '.[0].name')

#############################################

if [ -z "$first_name" ]; then
    echo "No matching torrent found."
    exit 1
fi

echo "Found:"
echo "  Name: $first_name"
echo
read -p "Do you want to download it? (y/n): " answer

case "$answer" in
    y|Y|yes|YES)
        MAGNET=$(piratebay -j info "$first_id" | jq -r '.magnet')
        echo "Adding to qBittorrent..."

        # Try qBittorrent GUI first, fallback to qbittorrent-nox
        if command -v qbittorrent >/dev/null 2>&1; then
            qbittorrent \
                --save-path="$SAVE_PATH" \
                --skip-dialog=true \
                "$MAGNET"
        elif command -v qbittorrent-nox >/dev/null 2>&1; then
            qbittorrent-nox \
                --save-path="$SAVE_PATH" \
                --skip-dialog=true \
                "$MAGNET"
        else
            echo "Error: Neither qbittorrent nor qbittorrent-nox is installed."
            exit 1
        fi
        
        echo "Download added."
        ;;
    *)
        echo "Cancelled."
        ;;
esac


