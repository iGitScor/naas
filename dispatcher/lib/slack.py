import slack
from dispatcher.lib.mongodb import AbstractModel, MongoCollection
from flask_pymongo import PyMongo
from pymongo import MongoClient
import urllib.parse

def send(message):
    client = slack.WebClient(token='---')

    client.chat_postMessage(
      channel='#general',
      text=message,
      link_names=True,
      icon_emoji="gina",
      username="Gina",
    )

    username = urllib.parse.quote_plus('racine')
    password = urllib.parse.quote_plus('carre')

    connection = MongoClient('mongodb://%s:%s@db' % (username, password))
    content = {"message": message}

    db = connection.naas
    notifCollection = db.Notification
    notifCollection.insert_one(content)
