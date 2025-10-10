python3 backend/arduino_reader.py &
uvicorn backend.server:app --host 0.0.0.0 --port 3000 --reload &
python3 frontend/dashboard_app/main.py