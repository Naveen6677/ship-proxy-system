# Step 1: Start the server (offshore proxy)

cd server
python server.py

# Step 2: Start the ship proxy (client)

cd ../client
python ship_proxy.py --host 127.0.0.1 --port 8888

# Step 3: Test with curl (HTTP/HTTPS)

curl.exe -x http://localhost:8888 http://httpbin.org/get
curl.exe -x http://localhost:8888 -X POST -d "key=value" http://httpbin.org/post
curl.exe -x http://localhost:8888 https://www.example.com/


