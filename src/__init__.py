import asyncio
import json
import logging
import os

import cv2
from aiohttp import web
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from xiaozhi_sdk import XiaoZhiWebsocket

from src.config import DEFAULT_MAC_ADDR, OTA_URL, PORT
from src.config.ice_config import ice_config
from src.track.audio import AudioFaceSwapper
from src.track.video import VideoFaceSwapper

# 设置 logger
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 禁用 aioice.ice 模块的日志输出
logging.getLogger("aioice.ice").setLevel(logging.WARNING)

ROOT = os.path.dirname(__file__)


def get_client_ip(request):
    """
    获取客户端真实IP地址
    按优先级尝试多种方式获取，确保在各种部署环境下都能正确获取IP
    """
    # 1. X-Real-IP: 反向代理设置的真实IP (Nginx, Apache等)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip != "unknown":
        return real_ip

    # 2. X-Forwarded-For: 代理链中的IP列表，取第一个
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 可能有多个IP，用逗号分隔，取第一个
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip and first_ip != "unknown":
            return first_ip

    # 3. CF-Connecting-IP: Cloudflare设置的真实IP
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip != "unknown":
        return cf_ip

    # 4. X-Client-IP: 某些代理使用的头
    client_ip = request.headers.get("X-Client-IP")
    if client_ip and client_ip != "unknown":
        return client_ip

    return "unknown"


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r", encoding="utf-8").read()
    return web.Response(content_type="text/html", text=content)


async def chatv2(request):
    content = open(os.path.join(ROOT, "chatv2.html"), "r", encoding="utf-8").read()
    return web.Response(content_type="text/html", text=content)


async def chat(request):
    content = open(os.path.join(ROOT, "chat.html"), "r", encoding="utf-8").read()
    return web.Response(content_type="text/html", text=content)


async def ice(request):
    """返回ICE服务器配置"""
    ice_servers_config = ice_config.get_ice_config()
    return web.Response(content_type="application/json", text=json.dumps(ice_servers_config, ensure_ascii=False))


async def offer(request):
    params = await request.json()
    _offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # 使用动态ICE服务器配置
    ice_servers = ice_config.get_server_ice_servers()
    configuration = RTCConfiguration(iceServers=ice_servers)
    pc = RTCPeerConnection(configuration=configuration)
    pcs.add(pc)

    # Store client IP in the peer connection object
    # 使用改进的IP获取函数
    pc.client_ip = get_client_ip(request)
    pc.mac_address = params.get("macAddress") or DEFAULT_MAC_ADDR

    await server(pc, _offer)

    return web.Response(
        content_type="application/json",
        text=json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}),
    )


pcs = set()


async def server(pc, offer):
    # Dictionary to store track instances

    # Create data channel for text messages
    channel = pc.createDataChannel("chat")

    async def message_handler_callback(message):
        logger.info("Received message: %s %s %s", pc.mac_address, pc.client_ip, message)
        channel.send(json.dumps(message, ensure_ascii=False))
        if message["type"] == "llm":
            pc.video_track.set_emoji(message["text"])

    xiaozhi = XiaoZhiWebsocket(message_handler_callback, ota_url=OTA_URL, audio_sample_rate=48000, audio_channels=2)

    def mcp_tool_func():
        def tool_set_volume(data):
            channel.send(json.dumps({"type": "tool", "text": "set_volume", "value": data["volume"]}))
            return "", False

        def tool_open_tab(data):
            channel.send(json.dumps({"type": "tool", "text": "open_tab", "value": data["url"]}))
            return "", False

        def tool_stop_music(data):
            channel.send(json.dumps({"type": "tool", "text": "stop_music"}))
            return "", False

        def tool_get_device_status(data):
            return (
                json.dumps(
                    {
                        "audio_speaker": {"volume": 100},
                        # 'screen': {'brightness': 75, 'theme': 'light'},
                        # 'network': {'type': 'wifi', 'ssid': 'wifi名称', 'signal': 'strong'}
                    }
                ),
                False,
            )

        def tool_take_photo(data):
            img_obj = xiaozhi.video_frame.to_ndarray(format="bgr24")
            # 直接使用 OpenCV 编码图片
            _, img_byte = cv2.imencode(".jpg", img_obj)
            img_byte = img_byte.tobytes()
            return img_byte, False

        from xiaozhi_sdk.utils.mcp_tool import (
            get_device_status,
            open_tab,
            play_custom_music,
            search_custom_music,
            set_volume,
            stop_music,
            take_photo,
        )

        take_photo["tool_func"] = tool_take_photo
        get_device_status["tool_func"] = tool_get_device_status
        set_volume["tool_func"] = tool_set_volume
        open_tab["tool_func"] = tool_open_tab
        stop_music["tool_func"] = tool_stop_music

        return [
            take_photo,
            get_device_status,
            set_volume,
            take_photo,
            open_tab,
            stop_music,
            search_custom_music,
            play_custom_music,
        ]

    await xiaozhi.set_mcp_tool(mcp_tool_func())
    await xiaozhi.init_connection(pc.mac_address)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info("Connection state is %s %s %s", pc.connectionState, pc.mac_address, pc.client_ip)
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            # Stop all AudioFaceSwapper instances

            await xiaozhi.close()
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            t = AudioFaceSwapper(xiaozhi, track)
            pc.addTrack(t)
            # 将 track 实例存储在 pc 对象上
            pc.audio_track = t
        elif track.kind == "video":
            t = VideoFaceSwapper(xiaozhi, track)
            pc.addTrack(t)
            # 将 track 实例存储在 pc 对象上
            pc.video_track = t

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)


async def on_shutdown(app):
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def run():
    app = web.Application()
    app.on_shutdown.append(on_shutdown)

    app.router.add_get("/", index)
    app.router.add_get("/chat", chat)
    app.router.add_get("/chatv2", chatv2)

    app.router.add_get("/api/ice", ice)
    app.router.add_post("/api/offer", offer)
    app.router.add_static("/static/", path=os.path.join(ROOT, "static"), name="static")

    web.run_app(app, host="0.0.0.0", port=PORT)
