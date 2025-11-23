PORT=5000

while true; do
    nc -l -p $PORT -q 1 | while read line; do
        case "$line" in
            ping)
                echo "pong"
                ;;
            status)
                echo "Running"
                ;;
            start_download*)
                magnet="${line#start_download }"
                echo "Starting download: $magnet"
                # call your bash torrent script here
                ;;
            *)
                echo "Unknown command: $line"
                ;;
        esac
    done
done

