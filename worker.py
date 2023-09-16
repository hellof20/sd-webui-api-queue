from google import pubsub_v1
import requests, json, time, os, sys
import redis
from loguru import logger

log_level= os.getenv('LOG_LEVEL')
subscription = os.getenv('SUBSCRIPTION')
redis_host = os.getenv('REDIS_HOST')
sd_api = os.getenv('SD_API', default = 'http://127.0.0.1:7860')
logger.debug(subscription)
logger.debug(redis_host)
logger.debug(log_level)
logger.debug(sd_api)
r = redis.Redis(host=redis_host, port=6379, db=0)

if log_level == 'debug':
    logger.remove()
    logger.add(sys.stdout, level='DEBUG')
else:
    logger.remove()
    logger.add(sys.stdout, level='INFO', format="<level>{time} | {level} | {message}</level>")

## pull的方式
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
    # logger.debug(parameters)
    respone = requests.post(sd_api+uri, json=parameters)
    return respone

while True:
    logger.info('Waiting request...')
    try:
        resp = pull_msg()
        if bool(resp):              
            ack_id = resp.received_messages[0].ack_id
            msg = resp.received_messages[0].message.data
            msg_id = resp.received_messages[0].message.message_id
            logger.debug("msg_id: " + msg_id)
            respone = send_request_sd_api(msg)
            logger.info(respone)
            if respone.status_code == 200:
                r.set(msg_id, respone.text)
                acknowledge(ack_id)              
                logger.info('msg_id: %s process success.' % msg_id)
            else:
                r.set(msg_id, respone.text)
                acknowledge(ack_id)
                logger.info('msg_id: %s process failed.' % msg_id)
        else:
            logger.info('Currently no request')
    except Exception as e:
        logger.error("request process failed.")
    time.sleep(1)

## 订阅的方式
# subscriber_client = pubsub_v1.SubscriberClient()
# subscription = subscriber_client.subscription_path("speedy-victory-336109", "sd-input-pull")
# def callback(message):
#     print(message)
#     message.ack()
# future = subscriber_client.subscribe(
#     subscription, callback)
# try:
#     future.result()
# except KeyboardInterrupt:
#     future.cancel()  # Trigger the shutdown.
#     future.result()  # Block until the shutdown is complete.
