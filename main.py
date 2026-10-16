import socket
import json
import threading
import requests
from google import genai


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
        input="your are professional in the field of phishing testing and cybersecurity, check if the link in this message is safe and similar to the original site: " + email_content
    )
    print(interaction.output_text)



