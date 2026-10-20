"""
HTTP front end for the GUI, sitting next to your existing main.py.

Your socket server in main.py speaks a custom JSON-over-TCP protocol
(ACTION / CONTENT) that a browser can't call directly — browsers only
speak HTTP. Rather than making the browser talk sockets, this Flask
app imports your scoring functions straight from main.py and calls
them in-process, then exposes one HTTP endpoint (/score) the GUI can
fetch() from.

Your main.py is untouched — start_server()/handle_client() still work
exactly as before if you want to run the socket side too; this file
just gives the browser-based GUI a way in.

Run it:
    pip install flask
    python web_app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, jsonify

from main import (
    check_http_links,
    check_text_quality,
    URL_PATTERN,
)

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/score", methods=["POST"])
def score():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")

    if not message.strip():
        return jsonify({"error": "message is empty"}), 400

    # --- pull links out of the pasted message and score them ---
    links = URL_PATTERN.findall(message)
    link_safety = check_http_links(links) if links else 100  # 100 = safe, drops per http:// link

    # --- run your spelling/grammar check on the message text ---
    text_safety, details = check_text_quality(message, score=100)

    # --- combine into one 0-100 *risk* score for the GUI (higher = riskier) ---
    combined_safety = (link_safety + text_safety) / 2
    risk_score = max(0, min(100, round(100 - combined_safety)))

    # --- turn what your checks found into the GUI's flag list ---
    flags = []

    http_links = [l for l in links if l.startswith("http://")]
    if http_links:
        flags.append({
            "label": f"{len(http_links)} unencrypted http:// link(s) found",
            "weight": len(http_links) * 10,
            "high": True,
        })

    if details["spelling_errors"]:
        flags.append({
            "label": f"{len(details['spelling_errors'])} misspelled word(s): "
                     + ", ".join(details["spelling_errors"][:5]),
            "weight": details["spelling_penalty"],
            "high": False,
        })

    if details["grammar_issues"]:
        flags.append({
            "label": f"{len(details['grammar_issues'])} grammar/style issue(s) found",
            "weight": details["grammar_penalty"],
            "high": False,
        })

    flags.sort(key=lambda f: f["weight"], reverse=True)

    return jsonify({"score": risk_score, "flags": flags})


if __name__ == "__main__":
    app.run(debug=True)
