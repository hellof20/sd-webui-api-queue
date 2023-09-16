from flask import Flask, request, abort
import redis
import os, sys, time, json
from loguru import logger
from google.cloud import pubsub_v1

app = Flask(__name__)

log_level= os.getenv('LOG_LEVEL')
topic_name = os.getenv('TOPIC_NAME')
redis_host = os.getenv('REDIS_HOST')
timeout = os.getenv('TIMEOUT', default = 20)
logger.debug(topic_name)
logger.debug(redis_host)
logger.debug(log_level)
logger.debug(timeout)

if log_level == 'debug':
    logger.remove()
    logger.add(sys.stdout, level='DEBUG')
else:
    logger.remove()
    logger.add(sys.stdout, level='INFO', format="<level>{time} | {level} | {message}</level>")

def pub_msg(topic, msg):
    publisher = pubsub_v1.PublisherClient()
    future = publisher.publish(topic, json.dumps(msg).encode('utf-8'))
    resp = future.result()
    return resp

@app.route('/sdapi/v1/<path:text>',methods = ['POST'])
def sdapi(text):
    result = ''
    data = {}
    data['path'] = request.path
    data['msg'] = request.json
    try:
        msg_id = pub_msg(msg = data, topic = topic_name)
        logger.debug("msg_id: " + msg_id)
    except Exception as e:
        logger.error('Write request to queue failed.')
        abort(500)
    try:
        r = redis.Redis(host=redis_host, port=6379, db=0)
        r.set(msg_id, '')
    except Exception as e:
        logger.error('Connect to Redis failed.')
        abort(500)
    num = 0
    while num < int(timeout)*2:
        value = r.get(msg_id)
        if value != b'':
            result = value
            break
        time.sleep(0.5)
        num += 1
    else:
        return 'Timeout'
    r.delete(msg_id)
    return result

if __name__ == '__main__':
    app.run(debug=True, port=8080, host='0.0.0.0')