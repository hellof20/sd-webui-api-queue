from google import pubsub_v1
import requests, json
from sd_pub import pub_msg
import GPUtil
import time
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

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

## pull的方式
client = pubsub_v1.SubscriberClient()
subscription="projects/speedy-victory-336109/subscriptions/sd-input-pull"

def pull_msg():
    request = pubsub_v1.PullRequest(
        subscription = subscription,
        max_messages = 1,
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
    sd_api = 'http://127.0.0.1:7860'
    msg = msg.decode('utf-8')
    dict = json.loads(msg)
    parameters = dict['msg']
    uri = dict['path']
    # print(type(parameters))
    # print(uri)
    x = requests.post(sd_api+uri, json = parameters)
    return x

while True:
    try:
        deviceID = GPUtil.getFirstAvailable()
        resp = pull_msg()
        print(resp)
        if bool(resp):
            ack_id = resp.received_messages[0].ack_id
            msg = resp.received_messages[0].message.data
            msg_id = resp.received_messages[0].message.message_id
            # print(ack_id)
            # print(msg.decode('utf-8'))
            resp = send_request_sd_api(msg)
            if resp.status_code == 200:
                r.set(msg_id, resp.text)
                # print(resp.text)
                acknowledge(ack_id)
                print('消息处理成功')
        else:
            print('no task')
    except:
        print('no Available GPU')
    time.sleep(1)


