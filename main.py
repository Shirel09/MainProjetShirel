import json
import socket
import threading
import requests
from google import genai

import re
from spellchecker import SpellChecker


def start_server():
    IP="127.0.0.1" #loopback
    Port = 5000
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((IP, Port))
    server_socket.listen()
    while True:
        client_socket,_ = server_socket.accept()
        threading.Thread(target=handle_client,args=(client_socket,)).start()



def handle_client(client_socket:socket.socket):
    while True:
        incoming_bytes = client_socket.recv(1024)
        msg = json.loads(incoming_bytes.decode("utf-8"))
        msg_action = msg["ACTION"]
        if msg_action == "CHECK_PHISHING":
            msg_content = msg["CONTENT"]
            email_address = msg_content["email_address"]
            email_content = msg_content["email_content"]
            links = msg_content["links"]
            links_score = check_http_links(links)


def check_http_links(links):
    score = 100
    for link in links:
        if link.startswith("http://"):
            score = score -10
    return score

def check_phishtank(links):
    response = requests.get("http://checkurl.phishtank.com/checkurl/url={}".format("https://classroom.google.com/"))
    print(response.json())

def check_content_with_ai(email_content):
    client = genai.Client()

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input="you are professional in the field of phishing testing and cybersecurity, check if the link in this message is safe and similar to the original site: " + email_content
    )
    print(interaction.output_text)


SPELLING_PENALTY = 3  # points lost for each misspelled word
SPELLING_MAX_PENALTY = 30  # spelling can never remove more than this
GRAMMAR_PENALTY = 2  # points lost for each grammar/style issue
GRAMMAR_MAX_PENALTY = 20  # grammar can never remove more than this

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")
WORD_PATTERN = re.compile(r"[A-Za-z']+")


def _clean_text(text):
    """Remove links and emails so they are not counted as spelling errors."""
    text = URL_PATTERN.sub(" ", text)
    text = EMAIL_PATTERN.sub(" ", text)
    return text


def find_spelling_errors(text, language="en"):
    """Return a list of words that are not in the dictionary."""
    spell = SpellChecker(language=language)
    words = WORD_PATTERN.findall(_clean_text(text))

    # Ignore very short words and words written in ALL CAPS (e.g. "PayPal", "USA")
    candidates = [w.lower() for w in words if len(w) > 2 and not w.isupper()]
    return sorted(spell.unknown(candidates))


def find_grammar_issues(text):
    """Simple rule-based grammar/style checks. Returns a list of issue descriptions."""
    issues = []
    cleaned = _clean_text(text)

    # 1. Repeated words: "please please click"
    for match in re.finditer(r"\b(\w+)\s+\1\b", cleaned, re.IGNORECASE):
        issues.append(f"repeated word: '{match.group(1)}'")

    # 2. Sentence that starts with a lowercase letter
    sentences = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    for s in sentences:
        if s and s[0].isalpha() and s[0].islower():
            issues.append(f"sentence starts with lowercase: '{s[:20]}...'")

    # 3. Too many exclamation / question marks: "Act now!!!"
    if re.search(r"[!?]{2,}", cleaned):
        issues.append("excessive punctuation (!! or ??)")

    # 4. Missing space after punctuation: "hello,click here"
    if re.search(r"[,;:][A-Za-z]", cleaned):
        issues.append("missing space after punctuation")

    # 5. Lots of words in ALL CAPS (shouting)
    words = WORD_PATTERN.findall(cleaned)
    caps = [w for w in words if len(w) > 3 and w.isupper()]
    if len(caps) >= 3:
        issues.append("too many ALL-CAPS words")

    return issues


def check_text_quality(text, score=100, language="en"):
    """
    Lower the safety score based on spelling and grammar errors.

    Args:
        text:     the message text written by the sender
        score:    starting safety score (default 100)
        language: dictionary language for the spell checker ("en", "es", "fr", "de", ...)

    Returns:
        (new_score, details) where details is a dict explaining what was found.
    """
    spelling_errors = find_spelling_errors(text, language)
    grammar_issues = find_grammar_issues(text)

    spelling_penalty = min(len(spelling_errors) * SPELLING_PENALTY, SPELLING_MAX_PENALTY)
    grammar_penalty = min(len(grammar_issues) * GRAMMAR_PENALTY, GRAMMAR_MAX_PENALTY)

    new_score = max(0, score - spelling_penalty - grammar_penalty)

    details = {
        "spelling_errors": spelling_errors,
        "grammar_issues": grammar_issues,
        "spelling_penalty": spelling_penalty,
        "grammar_penalty": grammar_penalty,
        "score_before": score,
        "score_after": new_score,
    }
    return new_score, details


if __name__ == "__main__":
    sample = (
        "Dear custumer, your acount has been suspnded!!! "
        "please verify verify your identity at http://example.com/login"
    )
    final_score, info = check_text_quality(sample, score=100)
    print("Final score:", final_score)
    for key, value in info.items():
        print(f"{key}: {value}")




