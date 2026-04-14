# 🔥 Bot Apostado Free Fire

Bot Discord de filas de apostas Free Fire no estilo Nulla.

## 📋 Como hospedar no Render

1. Crie uma conta no [Render](https://render.com)
2. Clique em **New > Web Service**
3. Conecte seu repositório GitHub ou faça upload dos arquivos
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. Vá em **Environment** e adicione:
   - `DISCORD_TOKEN` = seu token do bot Discord

## 🤖 Como obter o Token do Bot

1. Acesse [Discord Developer Portal](https://discord.com/developers/applications)
2. Crie uma aplicação nova
3. Vá em **Bot** > **Reset Token** > Copie o token
4. Em **Bot**, ative: **Presence Intent**, **Server Members Intent**, **Message Content Intent**
5. Em **OAuth2 > URL Generator**, selecione `bot` e `applications.commands`
6. Escolha as permissões: Administrator
7. Copie o link e adicione o bot ao seu servidor

## 📝 Comandos

| Comando | Descrição |
|---------|-----------|
| `/aposta` | Criar filas de apostas |
| `/mediador` | Configurar fila de mediadores |
| `/painel` | Painel de configuração (admin) |
| `/saldo` | Ver seu saldo |
| `/moedas` | Gerenciar moedas (admin) |
| `/loja` | Ver a loja |
| `/bancos` | Métodos de pagamento |
| `/faq` | Perguntas frequentes |
| `/pix` | Cadastrar chave Pix |
| `/help` | Lista de comandos |

## ✨ Funcionalidades

- Status rotativo "Assistindo" (troca a cada 15s)
- Embeds com barra lateral vermelha (estilo Nulla)
- Botões: Gelo infinito, Gelo normal, Sair da fila
- Sistema de filas 1x1, 2x2, 3x3, 4x4
- Painel de configuração com modals
- Sistema de moedas/saldo
- Fila de mediadores com botões
- 
