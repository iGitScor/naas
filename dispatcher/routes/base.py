from flask import Blueprint, request

from dispatcher.lib.slack import send as sendWithSlack 

base = Blueprint('base', __name__)

@base.route('/', methods=['POST'])
def notification():
    data = request.json
    
    if data['priority'] == 'alert':
        sendWithSlack(data['message'])

    return data
