from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    from applicacion.build_map import get_map  # move this inside
    map_html = get_map()._repr_html_()
    return render_template("index.html", map=map_html)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
