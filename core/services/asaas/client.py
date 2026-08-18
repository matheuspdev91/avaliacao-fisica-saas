import os

import requests


class AsaasClient:
    """Client HTTP para comunicação com API do Asaas"""

    def __init__(self):
        self.api_key = os.environ.get("ASAAS_API_KEY")
        self.environment = os.environ.get("ASAAS_ENVIRONMENT", "sandbox")

        if not self.api_key:
            raise RuntimeError("ASAAS_API_KEY não configurada")

        if self.environment == "production":
            self.api_key = os.environ.get("ASAAS_PRODUCTION_API_KEY")
            self.base_url = "https://api.asaas.com/v3"

        else:
            self.api_key = os.environ.get("ASAAS_SANDBOX_API_KEY")
            self.base_url = "https://api-sandbox.asaas.com/v3"

        if not self.api_key:
            raise RuntimeError(
                f"API KEY do Asaas não configurada para o ambiente:"
                f"{self.environment}"
            )

        self.headers = {
            "access_token": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "Fitflix/1.0",
        }

    def get_account(self):
        """Retorna os dados da conta autenticada no Asaas"""

        response = requests.get(
            f"{self.base_url}/myAccount",
            headers=self.headers,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    def create_customer(self, data):
        """Cria um cliente no Asaas"""

        response = requests.post(
            f"{self.base_url}/customers",
            headers=self.headers,
            json=data,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    def create_payment(self, data):
        """Cria uma cobrança no Asaas"""

        response = requests.post(
            f"{self.base_url}/payments",
            headers=self.headers,
            json=data,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()
