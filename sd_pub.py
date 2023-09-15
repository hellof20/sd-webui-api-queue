import os
import json
from google.cloud import pubsub_v1

def pub_msg(topic, msg):
    publisher = pubsub_v1.PublisherClient()
    future = publisher.publish(topic, json.dumps(msg).encode('utf-8'))
    resp = future.result()
    return resp

if __name__ == '__main__':
    msg = {'denoising_strength': 0, 'prompt': 'puppy dogs', 'negative_prompt': '', 'seed': -1, 'batch_size': 1, 'n_iter': 1, 'steps': 20, 'cfg_scale': 7, 'width': 512, 'height': 512, 'restore_faces': False, 'tiling': False, 'sampler_index': 'Euler'}
    print(pub_msg(msg))