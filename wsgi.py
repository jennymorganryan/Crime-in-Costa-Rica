from flask import Flask, render_template
from applicacion.build_map import get_map
import os

app = Flask(__name__, template_folder='applicacion/templates')

@app.route('/')
def home():
    m = get_map()
    map_html = m._repr_html_()
    return render_template('index.html', map=map_html)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # VERY IMPORTANT
    app.run(host="0.0.0.0", port=port, debug=False)

