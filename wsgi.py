import os
from flask import Flask, render_template
from pathlib import Path

app = Flask(__name__)

@app.route("/")
def home():
    # Only build map if not already built
    if not Path("static/map.html").exists():
        from applicacion.build_map import build_and_save_map
        build_and_save_map()
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
