import uuid
import json
import aiohttp
from typing import Any, Dict, List, Optional

class CannotConnect(RuntimeError):
    """Error to indicate we cannot connect."""

class InvalidCredentials(CannotConnect):
    """Error to indicate we cannot connect because of bad credentials."""

class ExpiredToken(CannotConnect):
    """Error to indicate we cannot connect because of an expired token."""

class TPLinkCloud:
    def __init__(self, username: str, password: str):
        self.session = aiohttp.ClientSession()
        self.username = username
        self.password = password
        self._token: Optional[str] = None

    async def _request(self, method: str, params: Dict[str, Any], attach_token: bool = True) -> Dict[str, Any]:
        headers = {
            'content-type': 'application/json',
            'accept': 'application/json'
        }
        payload = {
            "method": method,
            "params": params,
        }
        url = "https://wap.tplinkcloud.com"
        if attach_token:
            url += f"?token={self._token}"
        async with self.session.post(url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            body = await resp.json()

            if (error_code := body.get("error_code", 0)) != 0:
                error_msg = body.get("msg", "Unknown error")
                err = {
                    -20601: InvalidCredentials,
                    -20651: ExpiredToken,
                }.get(error_code, CannotConnect)
                raise err(f"{error_msg} ({error_code})")
            return body["result"]

    async def token(self, token: str) -> "TPLinkCloud":
        self._token = token
        return self
        
    def get_token(self) -> str:
        return self._token
        
    async def refresh_token(self) -> "TPLinkCloud":
        result = await self._request("login", {
            "appType": "Kasa_Android",
            "cloudUserName": self.username,
            "cloudPassword": self.password,
            "terminalUUID": str(uuid.uuid4()),
        }, attach_token=False)
        self._token = result["token"]
        return self

    async def login(self) -> "TPLinkCloud":
        return await self.refresh_token()
        
    async def list_devices(self) -> List["TPLinkDevice"]:
        result = await self._request("getDeviceList", {})
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
            "requestData": json.dumps({
                "system": {
                    "get_sysinfo": None,
                },
            }),
        })
        data = json.loads(result["responseData"])
        device = data["system"]["get_sysinfo"]

        self.setup(
            device_id=device["deviceId"],
            device_type=device.get("type", device.get("mic_type", None)),
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
            "requestData": json.dumps({
                "system": {
                    "set_relay_state": {
                        "state": state
                    }
                }
            }),
        })
        self._state = state
