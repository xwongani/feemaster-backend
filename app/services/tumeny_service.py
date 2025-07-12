import aiohttp
import logging

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

class TumenyService:
    def __init__(self):
        self.base_url = "https://tumeny.herokuapp.com/api"
        self.api_key = settings.TUMENY_API_KEY
        self.api_secret = settings.TUMENY_API_SECRET
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    async def _get_auth_token(self) -> str:

        """Get or refresh auth token from Tumeny """

        if self._token and self._token_expiry and datetime.utcnow() < self._token_expiry:
            return self._token

        url = f"{self.base_url}/token" headers = {"apiKey": self.api_key, "apiSecret": self.api_secret}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Failed to get Tumeny token:{response.status} {text}")
                    raise Exception(f"Tumeny token request failed:{response.status}")

                data = await response.json()
                self._token = data.get("token")
                expire_seconds = data.get("expireAt", 300)
                self._token_expiry = datetime.utcnow() + timedelta(seconds=expire_seconds - 30)

                logger.info("Tumeny auth token obtained")
                return self._token

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:

        """Create a payment request"""

        token = await self._get_auth_token()
        url = f"{self.base_url}/v1/payment"
        headers = {
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payment_data, headers=headers) as response:
                data = await response.json()
                if response.status != 200:
                    logger.error(f"Payment request failed:{response.status} {data}")
                    raise Exception(f"Payment request failed:{data}")
                return data

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:

        """Get payment status by payment ID """

        token = awaut self._get_auth_token()
        url = f"{self.base_url}/v1/payment/{payment_id}"
        headers = {"Authorization": f"Bearer {token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                if response.status != 200:
                    logger.error(f"Get payment status failed:{response.status} {data}")
                    raise Exception(f"Get payment status failed:{data}")
                return data


    async def send_sms(self, sender:str, message: str, recipient: str) -> Dict[str, Any]:

        """Send SMS"""

        token = await self._get_auth_token()
        url = f"{self.base_url}/v1/sms/send"
        headers = {
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"
        }
        payload = {
            "sender": sender,
            "message": message,
            "recipient": recipient
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if response.status != 200:
                    logger.error(f"Send SMS failed:{response.status} {data}")
                    raise Exception(f"Send SMS failed: {data}")
                return data

tumeny_service = TumenyService()
