import fbchat
from stone import FB_NAME, FB_PASS, FANTASY_LCS_CHAT

USERNAME = FB_NAME
PASSWORD = FB_PASS


def get_client(username=USERNAME ,password=PASSWORD):
    return fbchat.Client(username, password)


def send_message(msg, client, chat_id=FANTASY_LCS_CHAT):
    client.send(chat_id, msg)
