import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from datetime import datetime
from keep_alive import keep_alive

# ========== CONFIGURAÇÃO ==========
TOKEN = os.getenv("DISCORD_TOKEN")
EMBED_COLOR = 0xFF0000  # Vermelho como no estilo Nulla
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ========== DADOS EM MEMÓRIA ==========
filas = {}                    # Armazena as filas ativas
saldos = {}                   # Saldo dos jogadores
mediadores_fila = []          # Fila de mediadores
config_servidor = {}          # Configurações por servidor

# ========== STATUS ROTATIVO ==========
status_messages = [
    "🔥 Apostado FF Online",
    "🎮 Filas abertas!",
    "👥 Entre na fila agora",
    "💰 Apostas Free Fire",
    "🛡️ Mediadores disponíveis",
    "🏆 Sala de apostas ativa"
]
status_index = 0

@tasks.loop(seconds=15)
async def rotate_status():
    global status_index
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=status_messages[status_index % len(status_messages)]
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    status_index += 1

# ========== EVENTOS ==========
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user.name} está online!")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Servidores conectados: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} comandos sincronizados com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")
    rotate_status.start()

# ========== FUNÇÃO PARA CRIAR EMBED DA FILA (exatamente como no print) ==========
def criar_embed_fila(formato, tipo, valor, jogadores, imagem_url=None):
    titulo = f"Apostado {formato}"
    embed = discord.Embed(title=titulo, color=EMBED_COLOR)
    
    embed.add_field(name="📱 Plataforma", value=tipo, inline=True)
    embed.add_field(name="👥 Formato", value=formato, inline=True)
    embed.add_field(name="💰 Valor", value=f"R$ {valor}", inline=True)
    
    if jogadores:
        jogadores_text = "\n".join([f"<@{j}>" for j in jogadores])
    else:
        jogadores_text = "Nenhum jogador na fila."
    
    embed.add_field(name="🎮 Jogadores (0/2)", value=jogadores_text, inline=False)
    embed.set_footer(text="Clique no botão abaixo para entrar na fila!")
    
    if imagem_url and imagem_url.startswith("http"):
        embed.set_image(url=imagem_url)
    
    return embed

# ========== VIEW DA FILA (design idêntico ao print) ==========
class FilaView(discord.ui.View):
    def __init__(self, channel_id, fila_key):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.fila_key = fila_key

    @discord.ui.button(label="Entrar na Fila", style=discord.ButtonStyle.green, emoji="🎮")
    async def entrar_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        if self.fila_key not in filas:
            return await interaction.followup.send("❌ Esta fila não existe mais.", ephemeral=True)
        
        fila = filas[self.fila_key]
        if interaction.user.id in fila["jogadores"]:
            return await interaction.followup.send("⚠️ Você já está nesta fila!", ephemeral=True)
        
        fila["jogadores"].append(interaction.user.id)
        
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        
        await interaction.followup.send("✅ Você entrou na fila com sucesso!", ephemeral=True)
        
        # Verifica se atingiu 2 jogadores
        if len(fila["jogadores"]) >= 2:
            await self.iniciar_partida(interaction, fila)

    @discord.ui.button(label="Sair da Fila", style=discord.ButtonStyle.red, emoji="🏃")
    async def sair_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        if self.fila_key not in filas:
            return await interaction.followup.send("❌ Fila não encontrada.", ephemeral=True)
        
        fila = filas[self.fila_key]
        if interaction.user.id not in fila["jogadores"]:
            return await interaction.followup.send("⚠️ Você não está nesta fila!", ephemeral=True)
        
        fila["jogadores"].remove(interaction.user.id)
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send("✅ Você saiu da fila.", ephemeral=True)

    async def iniciar_partida(self, interaction, fila):
        jogadores_mention = " vs ".join([f"<@{j}>" for j in fila["jogadores"]])
        embed = discord.Embed(
            title="🎮 Partida Iniciada!",
            description=f"**{fila['formato']} {fila['tipo']}**\n**Valor:** R$ {fila['valor']}\n\n{jogadores_mention}",
            color=0x00FF00
        )
        await interaction.channel.send(embed=embed)
        # Limpa a fila após iniciar
        fila["jogadores"] = []

# ========== COMANDOS SLASH ==========
@bot.tree.command(name="aposta", description="Criar apostas no canal")
@app_commands.describe(
    tipo="Tipo de jogo",
    valores="Valores separados por vírgula (ex: 10,20,50)"
)
@app_commands.choices(tipo=[
    app_commands.Choice(name="Mobile", value="Mobile"),
    app_commands.Choice(name="Emulador", value="Emulador"),
    app_commands.Choice(name="Tático", value="Tático"),
    app_commands.Choice(name="Misto", value="Misto"),
])
async def aposta_criar(interaction: discord.Interaction, tipo: app_commands.Choice[str], valores: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores podem criar apostas!", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    # Detecta formato pelo nome do canal
    canal_nome = interaction.channel.name.lower()
    formato = "1x1"
    for f in ["4x4", "3x3", "2x2", "1x1"]:
        if f in canal_nome:
            formato = f
            break
    
    valores_lista = [v.strip() for v in valores.split(",") if v.strip()]
    
    for valor in valores_lista:
        try:
            float(valor)
        except ValueError:
            await interaction.followup.send(f"❌ Valor inválido: `{valor}`", ephemeral=True)
            continue
        
        valor_formatado = f"{float(valor):.2f}"
        
        fila_key = f"{interaction.channel.id}_{len(filas)}"
        fila_data = {
            "formato": formato,
            "tipo": tipo.value,
            "valor": valor_formatado,
            "jogadores": []
        }
        
        embed = criar_embed_fila(formato, tipo.value, valor_formatado, [])
        view = FilaView(interaction.channel.id, fila_key)
        
        msg = await interaction.channel.send(embed=embed, view=view)
        filas[fila_key] = fila_data
    
    await interaction.followup.send(f"✅ {len(valores_lista)} apostas criadas com sucesso!", ephemeral=True)

@bot.tree.command(name="painel", description="Abrir painel de configurações")
async def painel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores!", ephemeral=True)
    
    embed = discord.Embed(title="⚙️ Painel de Configuração", color=EMBED_COLOR)
    embed.description = "Configure o bot para este servidor"
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="saldo", description="Ver seu saldo")
async def saldo(interaction: discord.Interaction):
    valor = saldos.get(interaction.user.id, 0.0)
    embed = discord.Embed(title="💰 Seu Saldo", description=f"R$ {valor:.2f}", color=EMBED_COLOR)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== INICIALIZAÇÃO ==========
if __name__ == "__main__":
    keep_alive()   # Mantém o bot vivo no Render
    bot.run(TOKEN)
