from google import pubsub_v1
import requests, json, time, os, sys
import redis
from loguru import logger

log_level= os.getenv('LOG_LEVEL', default='INFO')
project_id = os.getenv('PROJECT_ID')
subscription = 'projects/'+project_id+'/subscriptions/'+os.getenv('MODEL_NAME')
model = os.getenv('MODEL_NAME') + '.safetensors'
redis_host = os.getenv('REDIS_HOST', default = '127.0.0.1')
sd_api = os.getenv('SD_API', default = 'http://127.0.0.1:7860')
logger.debug("subscription: %s" % subscription)
logger.debug("redis_host: %s" % redis_host)
logger.debug("log_level: %s" % log_level)
logger.debug("sd_api: %s" % sd_api)

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


client = pubsub_v1.SubscriberClient()
def pull_msg():
    request = pubsub_v1.PullRequest(
        subscription = subscription,
        max_messages = 1
        # return_immediately = True
    )
    response = client.pull(request=request,)
    return response


def acknowledge(ack_id):
    request = pubsub_v1.AcknowledgeRequest(
        subscription = subscription,
        ack_ids=[ack_id],
    )
    client.acknowledge(request=request)


def send_request_sd_api(msg):
    msg = json.loads(msg.decode('utf-8'))
    uri = msg['path']
    parameters = msg['msg']
    logger.debug(sd_api+uri)
    respone = requests.post(sd_api+uri, json=parameters)
    return respone

logger.info('change model ...')
time.sleep(30)
requests.post(sd_api+'/sdapi/v1/options', json={"sd_model_checkpoint": "%s" % model})


logger.info('Waiting request...')
while True:
    try:
        logger.debug('pulling ...')
        resp = pull_msg()
    except Exception as e:
        logger.error(e)
        break
    try:
        if bool(resp):
            ack_id = resp.received_messages[0].ack_id
            acknowledge(ack_id)            
            msg = resp.received_messages[0].message.data
            msg_id = resp.received_messages[0].message.message_id
            logger.debug("msg_id: " + msg_id)
            respone = send_request_sd_api(msg)
            logger.debug(respone)
            r.set(msg_id, respone.text)
            if respone.status_code == 200:
                logger.info('msg_id: %s process success.' % msg_id)
            else:
                logger.info('msg_id: %s process failed.' % msg_id)
    except Exception as e:
        logger.error(e)