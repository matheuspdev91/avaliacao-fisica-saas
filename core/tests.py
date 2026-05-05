from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from .forms import CriarAlunoForm
from .models import Aluno
from .views import gerar_senha_aleatoria


class CriarAlunoFormTests(TestCase):
    def test_form_rejeita_email_duplicado(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="duplicado@example.com",
            email="duplicado@example.com",
            password="Senha123",
        )

        form = CriarAlunoForm(
            data={
                "nome": "Aluno Duplicado",
                "email": "duplicado@example.com",
                "telefone": "",
                "data_nascimento": "2000-01-01",
                "objetivo": "",
                "observacoes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class CriarAlunoViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.professor = self.user_model.objects.create_user(
            username="professor@example.com",
            email="professor@example.com",
            password="Senha123",
        )

    def test_view_exige_login(self):
        response = self.client.get(reverse("core:criar_aluno"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core:login"), response.url)

    @patch("core.views.enviar_email_acesso_aluno")
    def test_cadastro_valido_cria_usuario_aluno_envia_email_e_redireciona(
        self, mock_enviar_email
    ):
        self.client.force_login(self.professor)

        response = self.client.post(
            reverse("core:criar_aluno"),
            data={
                "nome": "Maria Silva",
                "email": "maria@example.com",
                "telefone": "",
                "data_nascimento": "2001-04-15",
                "objetivo": "",
                "observacoes": "",
            },
        )

        self.assertRedirects(
            response, reverse("core:home"), fetch_redirect_response=False
        )

        usuario = self.user_model.objects.get(email="maria@example.com")
        aluno = Aluno.objects.get(user=usuario)

        self.assertEqual(usuario.username, "maria@example.com")
        self.assertEqual(aluno.nome, "Maria Silva")
        self.assertEqual(aluno.telefone, "")
        self.assertEqual(aluno.objetivo, "")
        self.assertEqual(aluno.observacoes, "")

        mock_enviar_email.assert_called_once()
        self.assertEqual(mock_enviar_email.call_args.kwargs["nome"], "Maria Silva")
        self.assertEqual(
            mock_enviar_email.call_args.kwargs["email"], "maria@example.com"
        )
        self.assertRegex(
            mock_enviar_email.call_args.kwargs["senha"], r"^[A-Za-z0-9]{8}$"
        )

        mensagens = [message.message for message in get_messages(response.wsgi_request)]
        self.assertTrue(
            any("Aluno cadastrado com sucesso" in mensagem for mensagem in mensagens)
        )

    @patch("core.views.enviar_email_acesso_aluno")
    def test_email_duplicado_nao_cria_aluno(self, mock_enviar_email):
        self.user_model.objects.create_user(
            username="maria@example.com",
            email="maria@example.com",
            password="Senha123",
        )
        self.client.force_login(self.professor)

        response = self.client.post(
            reverse("core:criar_aluno"),
            data={
                "nome": "Maria Silva",
                "email": "maria@example.com",
                "telefone": "",
                "data_nascimento": "2001-04-15",
                "objetivo": "",
                "observacoes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ja existe um usuario cadastrado com este email.")
        self.assertEqual(Aluno.objects.count(), 0)
        mock_enviar_email.assert_not_called()


class AlunoModelTests(TestCase):
    def test_idade_e_calculada_corretamente(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="aluno@example.com",
            email="aluno@example.com",
            password="Senha123",
        )

        hoje = date.today()
        data_nascimento = hoje.replace(year=hoje.year - 20)
        if hoje.month == 1 and hoje.day == 1:
            data_nascimento = date(hoje.year - 20, 12, 31)

        aluno = Aluno.objects.create(
            user=user,
            nome="Aluno Teste",
            data_nascimento=data_nascimento,
        )

        idade_esperada = (
            hoje.year
            - data_nascimento.year
            - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
        )
        self.assertEqual(aluno.idade, idade_esperada)


class SenhaAleatoriaTests(TestCase):
    def test_senha_gerada_tem_o_formato_esperado(self):
        senha = gerar_senha_aleatoria()
        self.assertRegex(senha, r"^[A-Za-z0-9]{8}$")
