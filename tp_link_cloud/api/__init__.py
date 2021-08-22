import uuid
import aiohttp
from typing import Any, Dict, List, Optional

class CannotConnect(RuntimeError):
    """Error to indicate we cannot connect."""

class InvalidCredentials(CannotConnect):
    """Error to indicate we cannot connect because of bad credentials."""

class TPLinkCloud:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.token: Optional[str] = None

    async def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "method": method,
            "params": params,
        }
        async with self.session.post("https://wap.tplinkcloud.com", json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()

            if (error_code := body.get("error_code", 0)) != 0:
                error_msg = body.get("msg", "Unknown error")
                if error_code == -20601:
                    raise InvalidCredentials(f"{error_msg} ({error_code})")
                else:
                    raise CannotConnect(f"{error_msg} ({error_code})")
            return body["result"]
        
    async def login(self, username: str, password: str) -> "TPLinkCloud":
        self.username = username
        self.password = password
        await self.refresh_token()
        return self
        
    async def refresh_token(self):
        result = await self._request("login", {
            "appType": "Kasa_Android",
            "cloudUserName": self.username,
            "cloudPassword": self.password,
            "terminalUUID": str(uuid.uuid4()),
        })
        self.token = result["token"]
        
    async def list_devices(self) -> List["TPLinkDevice"]:
        result = await self._request("getDeviceList", {
            "token": self.token,
        })
        devices = result["deviceList"]

        return [TPLinkDevice(
            cloud=self,
            device_id=device["deviceId"],
            device_type=device["deviceType"],
            alias=device["alias"],
            model=device["deviceModel"],
            name=device["deviceName"],
            software=device["fwVer"],
            state=device["status"],
        ) for device in devices]
    
class TPLinkDevice:
    def __init__(self, cloud: TPLinkCloud, *args, **kwargs):
        self.cloud = cloud
        self.setup(*args, **kwargs)

    def setup(self, device_id: str, device_type: str, alias: str, model: str, name: str, software: str, state: int = 0):
        self.device_id = device_id
        self.device_type = device_type
        self.alias = alias
        self.model = model
        self.name = name
        self.software = software
        self._state = state
        
    async def refresh(self):
        result = await self.cloud._request("passthrough", {
            "deviceId": self.device_id,
            "requestData": {
                "system": {
                    "get_sysinfo": None,
                },
            },
            "token": self.cloud.token
        })
        device = result["responseData"]["system"]["get_sysinfo"]

        self.setup(
            device_id=device["deviceId"],
            device_type=device["mic_type"],
            alias=device["alias"],
            model=device["model"],
            name=''.join(device["dev_name"]),
            software=''.join(device["sw_ver"]),
            state=device["relay_state"],
        )
        
    @property
    def state(self):
        return self._state
        
    async def set_state(self, state):
        await self.cloud._request("passthrough", {
            "deviceId": self.device_id,
            "requestData": {
                "system": {
                    "set_relay_state": {
                        "state": state
                    }
                }
            },
            "token": self.cloud.token,
        })
        self._state = state
