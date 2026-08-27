import os
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

LOG_PATH = r"C:\Users\Paulo Roberto\OneDrive\Documentos\Default Project\AI-Market-Analyzer\server.log"

def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

if __name__ == "__main__":
    try:
        log("Starting AI Market Analyzer server (uvicorn with default log)...")
        import uvicorn
        config = uvicorn.Config(
            "main:app",
            host="0.0.0.0",
            port=8000,
            log_config=None,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        log(f"ERROR: {e}")
