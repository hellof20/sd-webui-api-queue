from flask import Flask, request, abort, send_file, jsonify, Response
import redis
import os, sys, time, json
from loguru import logger
from google.cloud import pubsub_v1
import base64

app = Flask(__name__)

# topic_name = os.getenv('MODEL_NAME')
project_id = os.getenv('PROJECT_ID')
redis_host = os.getenv('REDIS_HOST', default = '127.0.0.1')
log_level= os.getenv('LOG_LEVEL', default='INFO')
timeout = os.getenv('TIMEOUT', default = 20)
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


@app.route('/',methods = ['GET'])
def get_images():
    msg_id = request.args.get('msg_id')
    if r.exists(msg_id):
        result = r.get(msg_id)
        if result:
            return result
        else:
            return "Task is running ... "
    else:
        return 'Task not exist'


@app.route('/sdapi/v1/<path:text>',methods = ['POST'])
def sdapi(text):
    result = ''
    data = {}
    data['path'] = request.path
    data['msg'] = request.json

    gcp_parameters = data['msg']['gcp_parameters']
    preview = gcp_parameters.get('preview')
    async_generate = gcp_parameters.get('async_generate')
    sd_model_checkpoint = gcp_parameters.get('sd_model_checkpoint')
    logger.debug("model: %s" % sd_model_checkpoint)

    try:
        msg_id = pub_msg(msg = data, topic = 'projects/'+project_id+'/topics/' + sd_model_checkpoint)
        logger.debug("msg_id: " + msg_id)
    except Exception as e:
        logger.error(e)
        abort(500, description='not supported model')
    if async_generate == True:
        r.set(msg_id, '')
        return msg_id
    else:
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
        if preview == True:
            json_result = json.loads(result)
            image_data = b''
            for image in json_result['images']:
                image_base64 = image
                image_data += base64.b64decode(image_base64)
            return Response(image_data, mimetype='image/jpeg')
        else:
            return result

if __name__ == '__main__':
    app.run(debug=True, port=8080, host='0.0.0.0')