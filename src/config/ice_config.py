import os
from typing import Any, Dict, List

from aiortc import RTCIceServer


class ICEConfig:
    """ICE服务器配置管理类"""

    def __init__(self):
        # 默认STUN服务器
        self.default_stun_urls = [
            "stun:stun.miwifi.com:3478",
            "stun:stun.l.google.com:19302",
            "stun:stun1.l.google.com:19302",
            "stun:stun.stunprotocol.org:3478",
        ]

    def get_ice_config(self) -> Dict[str, Any]:
        """获取前端ICE配置"""
        ice_servers = []

        # 添加默认STUN服务器
        for url in self.default_stun_urls:
            ice_servers.append({"urls": url})

        return {"iceServers": ice_servers, "iceCandidatePoolSize": 10, "iceTransportPolicy": "all"}

    def get_server_ice_servers(self) -> List[RTCIceServer]:
        """获取服务器端ICE服务器对象"""
        servers = []

        # 添加默认STUN服务器
        for url in self.default_stun_urls:
            servers.append(RTCIceServer(urls=url))

        return servers


# 全局实例
ice_config = ICEConfig()
