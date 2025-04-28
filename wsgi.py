from flask import Flask, render_template
from applicacion.build_map import get_map

app = Flask(__name__)

@app.route("/")
def home():
    map_object = get_map()  # build the map dynamically
    map_html = map_object._repr_html_()
    return render_template("index.html", map=map_html)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
