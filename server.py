from flask import Flask, request, abort
import redis
import os, sys, time, json
from loguru import logger
from google.cloud import pubsub_v1

app = Flask(__name__)

topic_name = os.getenv('TOPIC_NAME')
redis_host = os.getenv('REDIS_HOST')
log_level= os.getenv('LOG_LEVEL', default='INFO')
timeout = os.getenv('TIMEOUT', default = 20)
logger.debug("topic_name: %s" % topic_name)
logger.debug("redis_host: %s" % redis_host)
logger.debug("log_level: %s" % log_level)
logger.debug("timeout: %s" % timeout)

try:
    r = redis.Redis(host=redis_host, port=6379, db=0)
    r.ping()
except Exception as e:
    logger.error(e)
    sys.exit()

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
        logger.error(e)
        abort(500)
    num = 0
    while num < int(timeout):
        # logger.debug('check msg_id ...')
        if r.exists(msg_id):
            result = r.get(msg_id)
            logger.debug('msg_id value is: %s' % result)
            break
        time.sleep(0.5)
        num += 0.5
    else:
        result = 'Timeout'
    r.delete(msg_id)
    logger.debug('msg_id %s deleted from Redis.' % msg_id)
    return result

if __name__ == '__main__':
    app.run(debug=True, port=8080, host='0.0.0.0')