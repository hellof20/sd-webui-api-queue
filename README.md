# sd-webui-api-queue
[stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) 除了提供webui界面操作之外还提供了[API](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API)的方式和stable diffusion进行交互，可以实现text to image, image to image等功能。虽然webui界面的功能非常强大，但是在不同的业务使用场景下依然无法满足用户个性化的需求，因此用户自行开发UI界面然后对接API的模式更加通用和灵活。

由于stable-diffusion-webui提供的API是单机模式，对于大规模使用的场景下无法解决扩展性，性能和成本的问题。

sd-webui-api-queue的基本实现原理是在webui api前面部署API Server拦截用户的请求，将所有请求发送到消息队列。Worker组件监听消息队列，拿到用户的请求后转发给本地的stable diffusion，处理完成后将结果写入数据存储。API Server根据每个用户请求生成的唯一message id从数据存储中查询处理结果。原理架构如下:
![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/b5f81da6-9822-4c78-a1d9-57bb9c99ed22)

整个方案包含以下几个组成部分
- API Server

用户将请求发送到API Server（和stable-diffusion-webui原生API保持一致），API Server将用户请求的内容和uri组成消息写入消息队列，然后从数据存储中查询stable diffusion处理结果，查询到结果后返回给用户。如果一段时间内查询不到结果就返回Timeout.
- Queue

消息队列比较简单，提供消息队列的功能即可
- Worker

Worker和stable-diffusion-webui部署在同一台服务器或者同一个pod内，Worker监听到有消息之后调用本地的stable-diffusion-webui原生API进行处理，得到的处理后写入数据存储。
- Data

数据存储，提供数据存储和查询的能力

## GCP上的部署架构如下
![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/4daef31c-370d-4e6d-8404-3cd6f95bdc09)

### 架构说明
- API Server，Worker和stable-diffusion-webui部署在GKE中
- 消息队列采用托管的Pub/Sub，简单易用
- 数据存储采用托管的Redis, Redis可以提供快速的数据写入和查询能力
- stable-diffusion-webui涉及到模型文件，Lora等内容的共享，因此采用托管的Filestore在不同的stable-diffusion-webui共享和持久化存储
- GKE HPA根据从Cloud Monitoring中获取消息队列中未处理的消息数量，根据该指标进行弹性伸缩
- Artifact Registry提供Docker镜像仓库，API Server，Worker和stable-diffusion-webui的镜像都可以存放在Artifact Registry中

## 方案部署
1. 打开deploy.sh修改"Required parameters"部分内容
   ![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/51140f0f-e619-4169-b933-672f96f936fd)

其中PROJECT_ID, VPC_NETWORK, REGION, ZONE按实际情况填写，GKE_CLUSTER_NAME，REDIS_CLUSTER_NAME，FILESTORE_NAME可随意填写。SD_WEBUI_IMAGE需要特别注意，改为你自己的stable-diffusion-webui docker image的地址，如果没有现成的也可以参考GCP之前的[stable-diffusion-webui on GKE](https://github.com/GoogleCloudPlatform/stable-diffusion-on-gcp/tree/main/Stable-Diffusion-UI-GKE)方案进行构建.
2. 运行部署脚本
```
bash deploy.sh
```

## 文生图测试
1. 获取GKE credential
   ```
   gcloud container clusters get-credentials your_gke_cluster_name --region your_gke_clsuter_region
   ```
2. 获取API Server的Load Balancer外网地址
   ```
   kubectl get svc
   ```
### 参数说明
```
{
    "gcp_parameters": {
        "preview": true, // optional
        "async_generate": true, // optional
        "sd_model_checkpoint": "cuteyukimixAdorable_specialchapter" //must, do not include .safetensors
    },
    "prompt": "solo, 1girl, deep-yellow hair, medium bob cut, orange-colored eyes, brown boots, happy, :D, white shirts, orange-colored balloon skirt, sitting on big pumpkin tart, (pumpkin tart:1.4), pumpkin-pie, many pumpkins, grape vines,childbook,[(WHITE BACKGROUND:1.5),::5] HEXAGON",
    "negative_prompt": "NG_DeepNegative_V1_75T, EasyNegativeV2,  extra fingers, fewer fingers, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, (worst quality, low quality:1.4), Negative2, (low quality, worst quality:1.4), (bad anatomy), (inaccurate limb:1.2), bad composition, inaccurate eyes, extra digit,fewer digits, (extra arms:1.2), (bad-artist:0.6), bad-image-v2-39000",
    "batch_size": 1,
    "steps": 25,
    "width": 512,
    "height": 768,
    "cfg_scale": 7,
    "seed": 1598900424,
    "sampler_index": "DPM++ 2M Karras"
}
```
- preview表示是否在线预览图片
- async_generate表示是否为异步请求
- sd_model_checkpoint表示所使用的SD模型是什么，不包含.safetensors

### 同步请求并在线查看图片
- preview = true
- async_generate = false
这种方式便于调试和查看结果
![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/6d65130a-c480-476b-99ff-534e8d8f8b06)

   
### 异步请求获取结果
- async_generate = true
1. 异步请求立即返回id，后台生成图片
![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/f697c793-e11b-4ddf-9af7-f2d266167ecf)
2. 根据id查询生成结果
![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/97ff508f-86e4-494b-8d3a-541ba576e03f)

### 同步请求获取结果
- preview = false
- async_generate = false
![image](https://github.com/hellof20/sd-webui-api-queue/assets/8756642/6d4a8371-9c42-4d42-b1fa-f64b2137f0c6)



