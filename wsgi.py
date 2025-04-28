import os
from flask import Flask, render_template
from applicacion.build_map import get_map

app = Flask(__name__)

@app.route("/")
def home():
    map_html = get_map()._repr_html_()  # dynamically get the map when user opens
    return render_template("index.html", map=map_html)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # dynamic port for Render
    app.run(host="0.0.0.0", port=port)
