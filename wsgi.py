from main import app, init_db, check_endpoints_loop
import threading

# Initialize database
init_db()

# Start background thread
t = threading.Thread(target=check_endpoints_loop, daemon=True)
t.start()

if __name__ == "__main__":
    app.run()
