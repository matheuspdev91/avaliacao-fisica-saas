from django.conf import settings
from django.core.mail import send_mail


def enviar_email_acesso_aluno(
    *, nome, email, senha, login_url="http://127.0.0.1:8000/login/"
):
    assunto = "Seus dados de acesso"
    mensagem = (
        f"Ola, {nome}!\n\n"
        "Seu acesso foi criado com sucesso.\n\n"
        f"Login: {email}\n"
        f"Senha: {senha}\n"
        f"Link de acesso: {login_url}\n\n"
        "Se precisar de ajuda, entre em contato."
    )

    send_mail(
        subject=assunto,
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
