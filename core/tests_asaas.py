from django.test import TestCase, override_settings
from django.urls import reverse
import json
from unittest.mock import patch, MagicMock
from django.db import IntegrityError
from core.models import Assinatura, WebhookEvent, PagamentoAsaas

from django.contrib.auth import get_user_model
from core.services.asaas.client import AsaasClient
from core.services.asaas.exceptions import AsaasAuthenticationError, AsaasAPIError

User = get_user_model()


class WebhookTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="test_webhook@example.com",
            email="test_webhook@example.com",
            asaas_customer_id="cus_12345"
        )
        self.valid_token = "whsec_token123"

    def post_webhook(self, data, token=None):
        headers = {}
        if token:
            headers["HTTP_ASAAS_ACCESS_TOKEN"] = token
        return self.client.post(
            reverse("core:asaas_webhook"),
            data=json.dumps(data) if data else "",
            content_type="application/json",
            **headers
        )

    @override_settings(ASAAS_WEBHOOK_TOKEN="whsec_token123")
    def test_webhook_rejeita_get(self):
        resp = self.client.get(reverse("core:asaas_webhook"))
        self.assertEqual(resp.status_code, 405)

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_rejeita_token_invalido(self):
        resp = self.post_webhook({}, token="invalid")
        self.assertEqual(resp.status_code, 401)

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_rejeita_token_ausente(self):
        resp = self.post_webhook({})
        self.assertEqual(resp.status_code, 401)

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_rejeita_json_invalido(self):
        headers = {"HTTP_ASAAS_ACCESS_TOKEN": "whsec_token123"}
        resp = self.client.post(
            reverse("core:asaas_webhook"),
            data="not a json",
            content_type="application/json",
            **headers
        )
        self.assertEqual(resp.status_code, 400)

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_processa_payment_confirmed(self):

        Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_123",
            status="PENDING",
        )

        payload = {
            "id": "evt_001",
            "event": "PAYMENT_CONFIRMED",
            "payment": {
                "id": "pay_001",
                "customer": "cus_12345",
                "subscription": "sub_123",
                "value": 99.90,
                "dueDate": "2026-08-20",
            }
        }

        resp = self.post_webhook(payload, token=self.valid_token)
        self.assertEqual(resp.status_code, 200)

        assinatura = Assinatura.objects.get(usuario=self.user)
        self.assertEqual(assinatura.status, "PENDING")

        pagamento = PagamentoAsaas.objects.get(
            asaas_payment_id="pay_001"
        )

        self.assertEqual(pagamento.status, "CONFIRMED")

        evt = WebhookEvent.objects.get(event_id="evt_001")
        self.assertEqual(evt.status, "PROCESSED")

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_processa_payment_refunded(self):
        assinatura = Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_003",
            status="ACTIVE",
        )

        payload = {
            "id": "evt_003",
            "event": "PAYMENT_REFUNDED",
            "payment": {
                "id": "pay_003",
                "customer": "cus_12345",
                "subscription": "sub_003",
                "value": 99.90,
                "dueDate": "2026-08-20",
            },
        }

        resp = self.post_webhook(
            payload,
            token=self.valid_token,
        )

        self.assertEqual(resp.status_code, 200)

        assinatura.refresh_from_db()

        self.assertEqual(
            assinatura.status,
            "ACTIVE",
        )

        pagamento = PagamentoAsaas.objects.get(
            asaas_payment_id="pay_003"
        )

        self.assertEqual(
            pagamento.status,
            "REFUNDED",
        )

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_processa_payment_received(self):
        assinatura=Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_123",
            status="PENDING",
        )

        payload={
            "id": "evt_002",
            "event": "PAYMENT_RECEIVED",
           "payment": {
                "id": "pay_002",
                "customer": "cus_12345",
                "subscription": "sub_123",
                "value": 99.90,
                "dueDate": "2026-08-20",
                "paymentDate": "2026-08-21",
            }
        }
        resp=self.post_webhook(
            payload,
            token=self.valid_token,
        )

        self.assertEqual(resp.status_code, 200)

        assinatura.refresh_from_db()

        self.assertEqual(
            assinatura.status,
            "ACTIVE",
        )
        
        pagamento = PagamentoAsaas.objects.get(
            asaas_payment_id="pay_002"
        )

        self.assertEqual(
            pagamento.status,
            "RECEIVED",
        )

        self.assertEqual(
            pagamento.recebido_em.strftime("%Y-%m-%d"),
            "2026-08-21",
        )

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_evento_desconhecido_retorna_200(self):
        payload={
            "id": "evt_004",
            "event": "EVENTO_QUALQUER",
            "payment": {
                "id": "pay_004",
                "customer": "cus_12345"
            }
        }
        resp=self.post_webhook(payload, token=self.valid_token)
        self.assertEqual(resp.status_code, 200)

        evt=WebhookEvent.objects.get(event_id="evt_004")
        self.assertEqual(evt.status, "IGNORED")

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_idempotencia_evento_duplicado(self):

        Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_005",
            status="ACTIVE",
        )

        payload={
            "id": "evt_005",
            "event": "PAYMENT_CONFIRMED",
            "payment": {
                "id": "pay_005",
                "customer": "cus_12345",
                "subscription": "sub_005",
                "value": 99.90,
                "dueDate": "2026-08-20",
            }
        }

        # Envia primeira vez
        resp1=self.post_webhook(payload, token=self.valid_token)
        self.assertEqual(resp1.status_code, 200)

        # Envia segunda vez
        resp2=self.post_webhook(payload, token=self.valid_token)
        self.assertEqual(resp2.status_code, 200)

        # Deve haver apenas 1 evento no banco
        self.assertEqual(WebhookEvent.objects.filter(
            event_id="evt_005").count(), 1)

    @patch.dict('os.environ', {'ASAAS_WEBHOOK_TOKEN': 'whsec_token123'})
    def test_webhook_evento_fora_de_ordem(self):

        Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_006",
            status="ACTIVE",
        )
        # Atrasado chega primeiro
        payload1={
            "id": "evt_006",
            "event": "PAYMENT_OVERDUE",
            "payment": {
                "id": "pay_006",
                "customer": "cus_12345",
                "subscription": "sub_006",
                "value": 99.90,
                "dueDate": "2026-08-20",
            }
        }

        self.post_webhook(payload1, token=self.valid_token)

        assinatura=Assinatura.objects.get(usuario=self.user)
        self.assertEqual(assinatura.status, "ACTIVE")

        # Pago chega depois (isso deve ser permitido OVERDUE -> ACTIVE)
        payload2={
            "id": "evt_007",
            "event": "PAYMENT_CONFIRMED",
            "payment": {
                "id": "pay_006",
                "customer": "cus_12345",
                "subscription": "sub_006",
                "value": 99.90,
                "dueDate": "2026-08-20",
            }
        }


        self.post_webhook(payload2, token=self.valid_token)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, "ACTIVE")

        # Se depois chega outro OVERDUE, ele deve ignorar se o status for CANCELLED,
        # mas ACTIVE -> OVERDUE funciona.
        # Vamos testar CANCELLED -> OVERDUE (não deve regredir)
        assinatura.status="CANCELLED"
        assinatura.save()

        payload3={
            "id": "evt_008",
            "event": "PAYMENT_OVERDUE",
            "payment": {"id": "pay_006", "customer": "cus_12345"}
        }
        self.post_webhook(payload3, token=self.valid_token)
        assinatura.refresh_from_db()
        self.assertEqual(assinatura.status, "CANCELLED")  # Continuou CANCELLED

    @patch.dict(
        "os.environ",
        {"ASAAS_WEBHOOK_TOKEN": "whsec_token123"},
    )
    def test_payment_overdue_atualiza_pagamento_sem_inativar_assinatura(self):
        assinatura=Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_123",
            status="ACTIVE",
        )

        payload={
            "id": "evt_overdue_001",
            "event": "PAYMENT_OVERDUE",
            "payment": {
                "id": "pay_overdue_001",
                "customer": "cus_12345",
                "subscription": "sub_123",
                "value": 99.90,
                "dueDate": "2026-08-20",
            },
        }

        response=self.post_webhook(
            payload,
            token=self.valid_token,
        )

        self.assertEqual(response.status_code, 200)

        assinatura.refresh_from_db()

        self.assertEqual(
            assinatura.status,
            "ACTIVE",
        )

        pagamento=PagamentoAsaas.objects.get(
            asaas_payment_id="pay_overdue_001"
        )

        self.assertEqual(
            pagamento.status,
            "OVERDUE",
        )


class AsaasClientTests(TestCase):

    @patch.dict(
        'os.environ',
        {
            'ASAAS_ENVIRONMENT': 'sandbox',
            'ASAAS_SANDBOX_API_KEY': '123',
        }
    )
    def test_client_seleciona_sandbox_corretamente(self):
        client = AsaasClient()

        self.assertEqual(
            client.base_url,
            "https://api-sandbox.asaas.com/v3"
        )
        self.assertEqual(
            client.api_key,
            "123"
        )

    @patch.dict(
        'os.environ',
        {
            'ASAAS_ENVIRONMENT': 'production',
            'ASAAS_PRODUCTION_API_KEY': '456',
        }
    )
    def test_client_seleciona_producao_corretamente(self):
        client = AsaasClient()

        self.assertEqual(
            client.base_url,
            "https://api.asaas.com/v3"
        )
        self.assertEqual(
            client.api_key,
            "456"
        )

    @patch.dict(
        'os.environ',
        {
            'ASAAS_ENVIRONMENT': 'sandbox',
            'ASAAS_SANDBOX_API_KEY': '',
        }
    )
    def test_client_falha_sem_api_key(self):
        with self.assertRaises(RuntimeError):
            AsaasClient()

    @patch.dict(
        'os.environ',
        {
            'ASAAS_ENVIRONMENT': 'sandbox',
            'ASAAS_SANDBOX_API_KEY': '123',
        }
    )
    @patch('core.services.asaas.client.requests.request')
    def test_client_get_payment(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "pay_123"
        }
        mock_request.return_value = mock_response

        client = AsaasClient()
        data = client.get_payment("pay_123")

        self.assertEqual(
            data["id"],
            "pay_123"
        )

        mock_request.assert_called_with(
            "GET",
            "https://api-sandbox.asaas.com/v3/payments/pay_123",
            headers={
                "access_token": "123",
                "Content-Type": "application/json",
                "User-Agent": "Fitflix/1.0"
            },
            timeout=10
        )

    @patch.dict(
        'os.environ',
        {
            'ASAAS_ENVIRONMENT': 'sandbox',
            'ASAAS_SANDBOX_API_KEY': '123',
        }
    )
    @patch('core.services.asaas.client.requests.request')
    def test_client_create_subscription(self, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "sub_123",
            "status": "ACTIVE",
        }
        mock_request.return_value = mock_response

        client = AsaasClient()

        payload = {
            "customer": "cus_12345",
            "billingType": "PIX",
            "value": 99.90,
            "cycle": "MONTHLY",
            "nextDueDate": "2026-09-01",
            "description": "Fitflix - Plano Mensal",
        }

        data = client.create_subscription(payload)

        self.assertEqual(
            data["id"],
            "sub_123",
        )

        mock_request.assert_called_with(
            "POST",
            "https://api-sandbox.asaas.com/v3/subscriptions",
            headers={
                "access_token": "123",
                "Content-Type": "application/json",
                "User-Agent": "Fitflix/1.0",
            },
            json=payload,
            timeout=10,
        )


class PagamentoAsaasTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="pagamento@example.com",
            email="pagamento@example.com",
            asaas_customer_id="cus_pagamento_123",
        )

        self.assinatura=Assinatura.objects.create(
            usuario=self.user,
            asaas_subscription_id="sub_123",
            status="ACTIVE",
        )

    def test_assinatura_pode_ter_varios_pagamentos(self):
        pagamento1=PagamentoAsaas.objects.create(
            assinatura=self.assinatura,
            asaas_payment_id="pay_001",
            valor="99.90",
        )

        pagamento2=PagamentoAsaas.objects.create(
            assinatura=self.assinatura,
            asaas_payment_id="pay_002",
            valor="99.90",
        )

        self.assertEqual(
            self.assinatura.pagamentos.count(),
            2,
        )

        self.assertEqual(
            pagamento1.status,
            "PENDING",
        )

        self.assertEqual(
            pagamento2.status,
            "PENDING",
        )

    def test_asaas_payment_id_deve_ser_unico(self):
        PagamentoAsaas.objects.create(
            assinatura=self.assinatura,
            asaas_payment_id="pay_unico",
            valor="99.90",
        )

        with self.assertRaises(IntegrityError):
            PagamentoAsaas.objects.create(
                assinatura=self.assinatura,
                asaas_payment_id="pay_unico",
                valor="99.90",
            )