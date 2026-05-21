from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("alunos/novo/", views.criar_aluno, name="criar_aluno"),
    # Avaliações completas
    path("avaliacoes/nova/", views.criar_avaliacao, name="criar_avaliacao"),
    path(
        "avaliacoes/<int:id>/editar/", views.editar_avaliacao, name="editar_avaliacao"
    ),
    path(
        "avaliacoes/<int:id>/excluir/",
        views.excluir_avaliacao,
        name="excluir_avaliacao",
    ),
    path("avaliacoes/<int:id>/", views.detalhe_avaliacao, name="detalhe_avaliacao"),
    path("avaliacoes/", views.avaliacoes, name="avaliacoes"),
    path("avaliacoes/escolher-tipo/", views.escolher_tipo, name="escolher_tipo"),
    path(
        "avaliacoes/idoso/", views.criar_avaliacao_idoso, name="criar_avaliacao_idoso"
    ),
    path(
        "avaliacoes/crianca/",
        views.criar_avaliacao_crianca,
        name="criar_avaliacao_crianca",
    ),
    path(
        "treino/<int:treino_id>/exercicio/adicionar/",
        views.adicionar_exercicio,
        name="adicionar_exercicio",
    ),
    # Dashboard
    path("dashboard/<int:id>/", views.dashboard, name="dashboard"),
    # FitFlix
    path("fitflix/", views.fitflix, name="fitflix"),
    path("exercicios/novo/", views.criar_exercicio, name="criar_exercicio"),
    path("exercicio/<int:id>/", views.exercicio_detalhe, name="exercicio_detalhe"),
    path("treinos/novo/", views.criar_treino, name="criar_treino"),
    path("grupo/<int:id>/", views.lista_exercicios, name="lista_exercicios"),
    # Treinos
    path("treino/<int:treino_id>/", views.treino_detail, name="treino_detail"),
    path("aluno/<int:aluno_id>/", views.painel_aluno, name="painel_aluno"),
    path("treino/<uuid:token>/", views.ver_treino, name="ver_treino"),
    # Reset Password
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html"
        ),
        name="password_reset",
    ),
    # Editar treino
    path("treino/<int:treino_id>/editar/", views.editar_treino, name="editar_treino"),

    #vincular gifs
    path(
    "vincular-gifs/",
    views.vincular_gifs,
    name="vincular_gifs"
),

]
