import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, Message, MessageSegment
from nonebot.params import CommandArg, ArgStr
from nonebot.typing import T_State

from deep_translator import MyMemoryTranslator, GoogleTranslator

txt2img = on_command("draw", aliases={"dream"}, priority=5, block=True)
txt2img_cn = on_command("cn", aliases={"cn_draw", "cn_dream", "draw_cn"}, priority=5, block=True)

import redis
import json

config = nonebot.get_driver().config
redis_host_address = config.redis_host_address
redis_host_port = config.redis_host_port
redis_db_number = config.redis_db_number
redis_password = config.redis_password
proxy_addr = config.proxy_addr

proxies = {
    "https": proxy_addr,
    "http": proxy_addr
}

mymemory_translator = MyMemoryTranslator(source="zh-CN", target="en")
google_translator = GoogleTranslator(source='auto', target='en', proxies=proxies)

REDIS_JOB_QUEUE_NAME = config.redis_job_queue_name
REDIS_RESULT_QUEUE_NAME = config.redis_result_queue_name
REDIS_ERROR_QUEUE_NAME = config.redis_error_queue_name
IMAGE_SAVE_PATH = config.image_save_path

r = redis.Redis(host=redis_host_address, port=redis_host_port, db=redis_db_number, password=redis_password) #connect to server

from PIL import Image
from io import BytesIO

import re
import os
import queue
import time

from concurrent.futures import ThreadPoolExecutor

def background_consumer(r, image_save_path, redis_result_queue_name):
    while True:
        try:
            img_bytes = r.blpop(REDIS_RESULT_QUEUE_NAME, 1)
            if img_bytes is not None:
                img_tmp = Image.open(BytesIO(img_bytes[1]))
                job_dict = json.loads(img_tmp.text["job_dict_json:"])
                user_id = job_dict['user_id']
                filename = str(user_id) + '_' + re.sub('[\W_]+', '', job_dict['txt_str']) + '.jpg'
                img_path = os.path.join(image_save_path, filename)
                img_tmp.save(img_path)
                r.set(user_id, img_path)
        except Exception as e:
            print(e)

executor = ThreadPoolExecutor(2)
executor.submit(background_consumer, r, IMAGE_SAVE_PATH, REDIS_RESULT_QUEUE_NAME)

@txt2img.handle()
async def _(state: T_State, arg: Message = CommandArg()):
    if arg.extract_plain_text().strip():
        state["txt"] = arg.extract_plain_text().strip()

@txt2img_cn.handle()
async def _(state: T_State, arg: Message = CommandArg()):
    if arg.extract_plain_text().strip():
        state["txt"] = arg.extract_plain_text().strip()

@txt2img.got("txt", prompt="Text is required to generate images")
async def _(bot: Bot, event: MessageEvent, state: T_State, txt_str: str = ArgStr("txt")):
    await txt2img.send("Trying to draw txt: " + txt_str, at_sender=True)
    user_id = event.user_id
    img_out_path = await process_prompt(txt_str, user_id)
    msg_image = MessageSegment.image('file://' + img_out_path.decode('utf-8'))
    await txt2img.send(msg_image, at_sender=True)

@txt2img_cn.got("txt", prompt="Text is required to generate images")
async def _(bot: Bot, event: MessageEvent, state: T_State, txt_cn: str = ArgStr("txt")):
    try:
        txt_str = google_translator.translate(txt_cn)
        await txt2img_cn.send("drawing translated txt:" + txt_str, at_sender=True)
    except Exception as e:
        await txt2img_cn.send("failed to translate to english, " + str(e), at_sender=True)
        return
    user_id = event.user_id
    img_out_path = await process_prompt(txt_str, user_id)
    msg_image = MessageSegment.image('file://' + img_out_path.decode('utf-8'))
    await txt2img_cn.send(msg_image, at_sender=True)

async def process_prompt(txt_str: str, user_id: int):
    d = {}
    d['user_id'] = user_id
    d['txt_str'] = str(txt_str)
    d['scale'] = "7.5"
    d['n_samples'] = 1
    d['n_iter'] = 1
    d['ddim_steps'] = 50
    d['ddim_eta'] = 0.0
    #d['created_at'] = str(self.created_at)
    #d['started_at'] = str(self.created_at)
    #d['finished_at'] = str(self.finished_at)
    r.rpush(REDIS_JOB_QUEUE_NAME, json.dumps(d))
    while True:
        redis_img_path = r.get(user_id)
        if redis_img_path is not None:
            print(redis_img_path)
            r.delete(user_id)
            return redis_img_path
        else:
            time.sleep(3)
