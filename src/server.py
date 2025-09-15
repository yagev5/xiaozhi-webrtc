import json
import logging

import cv2
from xiaozhi_sdk import XiaoZhiWebsocket

from src.config import OTA_URL

logger = logging.getLogger(__name__)


class XiaoZhiServer(object):
    def __init__(self, pc):
        self.pc = pc
        self.channel = pc.createDataChannel("chat")
        self.server = None

    async def message_handler_callback(self, message):
        logger.info("Received message: %s %s %s", self.pc.mac_address, self.pc.client_ip, message)
        # if message["type"] == "websocket" and message["state"] == "close":
        #     await self.start()
        #     return

        self.channel.send(json.dumps(message, ensure_ascii=False))
        if message["type"] == "llm":
            self.pc.video_track.set_emoji(message["text"])

    async def start(self):
        self.server = XiaoZhiWebsocket(
            self.message_handler_callback, ota_url=OTA_URL, audio_sample_rate=48000, audio_channels=2
        )
        await self.server.set_mcp_tool(self.mcp_tool_func())
        await self.server.init_connection(self.pc.mac_address)

    def mcp_tool_func(self):
        def tool_set_volume(data):
            self.channel.send(json.dumps({"type": "tool", "text": "set_volume", "value": data["volume"]}))
            return "", False

        def tool_open_tab(data):
            self.channel.send(json.dumps({"type": "tool", "text": "open_tab", "value": data["url"]}))
            return "", False

        def tool_stop_music(data):
            self.channel.send(json.dumps({"type": "tool", "text": "stop_music"}))
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
            img_obj = self.server.video_frame.to_ndarray(format="bgr24")
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
