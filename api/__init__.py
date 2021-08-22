import uuid
import aiohttp
from typing import List, Optional

class TPLinkCloud:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.token: Optional[str] = None
        
    async def login(self, username: str, password: str) -> "TPLinkCloud":
        self.username = username
        self.password = password
        await self.refresh_token()
        return self
        
    async def refresh_token(self):
        payload = {
            "method": "login",
            "params": {
                "appType": "Kasa_Android",
                "cloudUserName": self.username,
                "cloudPassword": self.password,
                "terminalUUID": str(uuid.uuid4()),
            }
        }
        async with self.session.post("https://wap.tplinkcloud.com", json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()
            print(body)
            self.token = body["result"]["token"]
        
    async def list_devices(self) -> List["TPLinkDevice"]:
        payload = {
            "method": "getDeviceList",
            "params": {
                "token": self.token,
            }
        }
        async with self.session.post("https://wap.tplinkcloud.com", json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()
            devices = body["result"]["deviceList"]

        return [TPLinkDevice(
            cloud=self,
            device_id=device["deviceId"],
            device_type=device["deviceType"],
            alias=device["alias"],
            model=device["deviceModel"],
            name=device["deviceName"],
            state=device["status"],
        ) for device in devices]
    
class TPLinkDevice:
    def __init__(self, cloud: TPLinkCloud, *args, **kwargs):
        self.cloud = cloud
        self.setup(*args, **kwargs)

    def setup(self, device_id: str, device_type: str, alias: str, model: str, name: str, state: int = 0):
        self.device_id = device_id
        self.device_type = device_type
        self.alias = alias
        self.model = model
        self.name = name
        self._state = state
        
    async def refresh(self):
        payload = {
            "method": "passthrough",
            "params": {
                "deviceId": self.device_id,
                "requestData": {
                    "system": {
                        "get_sysinfo": None,
                    },
                },
                "token": self.cloud.token
            }
        }
        async with self.cloud.session.post("https://wap.tplinkcloud.com", json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()
            device = body["result"]["responseData"]["system"]["get_sysinfo"]

        self.setup(
            device_id=device["deviceId"],
            device_type=device["mic_type"],
            alias=device["alias"],
            model=device["model"],
            name=''.join(device["dev_name"]),
            state=device["relay_state"],
        )
        
    @property
    def state(self):
        return self._state
        
    async def set_state(self, state):
        payload = {
            "method": "passthrough",
            "params": {
                "deviceId": self.device_id,
                "requestData": {
                    "system": {
                        "set_relay_state": {
                            "state": state
                        }
                    }
                },
                "token": self.cloud.token,
            }
        }
        async with self.cloud.session.post("https://wap.tplinkcloud.com", json=payload) as resp:
            resp.raise_for_status()

        self._state = state
