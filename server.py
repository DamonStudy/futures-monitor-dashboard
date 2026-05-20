"""Start the futures monitor dashboard from the project root."""

from src.server import app


if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", "8010"))
    app.run(host="127.0.0.1", port=port, debug=False)
