from flask import Flask,request
from sd_pub import pub_msg
import redis
import time

app = Flask(__name__)

@app.route('/sdapi/v1/<path:text>',methods = ['POST'])
def sdapi(text):
    result = ''
    data = {}
    data['path'] = request.path
    data['msg'] = request.json
    input_topic = 'projects/speedy-victory-336109/topics/sd-input'
    msg_id = pub_msg(msg = data, topic = input_topic)
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.set(msg_id, '')
    num = 0
    while num < 10:
        value = r.get(msg_id)
        if value != b'':
            result = value
            break
        time.sleep(0.5)
        num += 1
    else:
        return 'timeout'
    return result

if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')