import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from datetime import datetime
from keep_alive import keep_alive

# ========== CONFIGURAÇÃO ==========
TOKEN = os.getenv("DISCORD_TOKEN")
EMBED_COLOR = 0xFF0000  # Vermelho (barra lateral)
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ========== DADOS EM MEMÓRIA ==========
filas = {}  # {channel_id: {"formato": str, "valor": str, "tipo": str, "jogadores": [], "msg_id": int}}
saldos = {}  # {user_id: float}
mediadores_fila = []  # lista de user_ids
config_servidor = {}  # {guild_id: {"cargo_mediador": int, "canal_logs": int, "categoria_apostas": int, "cor": int}}

# ========== STATUS ROTATIVO ==========
status_messages = [
    "Apostado FF",
    "Filas abertas!",
    "Entre na fila!",
    "Free Fire Apostas",
    "Apostado Online",
    "Mediadores disponíveis",
    "Sala de apostas",
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
    print(f"📡 Servidores: {len(bot.guilds)}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} comandos sincronizados!")
    except Exception as e:
        print(f"❌ Erro ao sincronizar: {e}")
    rotate_status.start()

# ========== FUNÇÕES AUXILIARES ==========
def criar_embed_fila(formato, tipo, valor, jogadores, imagem_url=None):
    """Cria embed no estilo Nulla"""
    titulo = f"{formato} | Apostado Free Fire"
    embed = discord.Embed(
        title=titulo,
        color=EMBED_COLOR
    )
    embed.add_field(name="》Formato", value=f"{formato} {tipo}", inline=True)
    embed.add_field(name="⚡ Valor", value=f"R$ {valor}", inline=True)
    
    if jogadores:
        jogadores_text = "\n".join([f"Normal. | <@{j}>" for j in jogadores])
    else:
        jogadores_text = "Sem jogadores..."
    
    embed.add_field(name="👥 Jogadores", value=jogadores_text, inline=False)
    
    agora = datetime.now()
    embed.set_footer(text=agora.strftime("%d/%m/%Y %H:%M"))
    
    if imagem_url:
        embed.set_thumbnail(url=imagem_url)
    
    return embed

class FilaView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Gelo infinito", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def gelo_infinito(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel_id not in filas:
            return await interaction.response.send_message("❌ Fila não encontrada.", ephemeral=True)
        
        fila = filas[self.channel_id]
        user_id = interaction.user.id
        
        if user_id in fila["jogadores"]:
            return await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)
        
        fila["jogadores"].append(user_id)
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você entrou na fila com **Gelo infinito**!", ephemeral=True)
        
        max_jogadores = int(fila["formato"].split("x")[0]) * 2
        if len(fila["jogadores"]) >= max_jogadores:
            await iniciar_partida(interaction, fila)

    @discord.ui.button(label="Gelo normal", style=discord.ButtonStyle.secondary, emoji="🧊")
    async def gelo_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel_id not in filas:
            return await interaction.response.send_message("❌ Fila não encontrada.", ephemeral=True)
        
        fila = filas[self.channel_id]
        user_id = interaction.user.id
        
        if user_id in fila["jogadores"]:
            return await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)
        
        fila["jogadores"].append(user_id)
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você entrou na fila com **Gelo normal**!", ephemeral=True)
        
        max_jogadores = int(fila["formato"].split("x")[0]) * 2
        if len(fila["jogadores"]) >= max_jogadores:
            await iniciar_partida(interaction, fila)

    @discord.ui.button(label="Sair da fila", style=discord.ButtonStyle.primary, emoji="🚪")
    async def sair_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel_id not in filas:
            return await interaction.response.send_message("❌ Fila não encontrada.", ephemeral=True)
        
        fila = filas[self.channel_id]
        user_id = interaction.user.id
        
        if user_id not in fila["jogadores"]:
            return await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)
        
        fila["jogadores"].remove(user_id)
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você saiu da fila!", ephemeral=True)

class EntrarFilaView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Entrar na fila", style=discord.ButtonStyle.secondary)
    async def entrar_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel_id not in filas:
            return await interaction.response.send_message("❌ Fila não encontrada.", ephemeral=True)
        
        fila = filas[self.channel_id]
        user_id = interaction.user.id
        
        if user_id in fila["jogadores"]:
            return await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)
        
        fila["jogadores"].append(user_id)
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você entrou na fila!", ephemeral=True)

    @discord.ui.button(label="Sair da fila", style=discord.ButtonStyle.primary, emoji="🚪")
    async def sair_fila(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.channel_id not in filas:
            return await interaction.response.send_message("❌ Fila não encontrada.", ephemeral=True)
        
        fila = filas[self.channel_id]
        user_id = interaction.user.id
        
        if user_id not in fila["jogadores"]:
            return await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)
        
        fila["jogadores"].remove(user_id)
        embed = criar_embed_fila(fila["formato"], fila["tipo"], fila["valor"], fila["jogadores"])
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você saiu da fila!", ephemeral=True)

async def iniciar_partida(interaction, fila):
    """Quando a fila enche, inicia a partida"""
    jogadores_mention = " ".join([f"<@{j}>" for j in fila["jogadores"]])
    embed = discord.Embed(
        title="🎮 Partida Encontrada!",
        description=f"**Formato:** {fila['formato']} {fila['tipo']}\n**Valor:** R$ {fila['valor']}\n\n**Jogadores:**\n{jogadores_mention}",
        color=0x00FF00
    )
    embed.set_footer(text="Boa sorte a todos! 🔥")
    await interaction.channel.send(embed=embed)
    fila["jogadores"] = []

# ========== COMANDOS SLASH ==========

# --- /aposta criar ---
@bot.tree.command(name="aposta", description="Criar filas de apostas no canal")
@app_commands.describe(
    tipo="Tipo de jogo (Mobile, Emulador, Tático, Misto)",
    valores="Valores separados por vírgula (ex: 20,10,5.50)"
)
@app_commands.choices(tipo=[
    app_commands.Choice(name="Mobile", value="Mobile"),
    app_commands.Choice(name="Emulador", value="Emulador"),
    app_commands.Choice(name="Tático", value="Tático"),
    app_commands.Choice(name="Misto", value="Misto"),
])
async def aposta_criar(interaction: discord.Interaction, tipo: app_commands.Choice[str], valores: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores podem criar filas!", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    # Detectar formato pelo nome do canal
    canal_nome = interaction.channel.name.lower()
    formato = "1x1"  # padrão
    for f in ["4x4", "3x3", "2x2", "1x1"]:
        if f in canal_nome:
            formato = f
            break
    
    valores_lista = [v.strip() for v in valores.split(",")]
    
    guild_icon = interaction.guild.icon.url if interaction.guild.icon else None
    
    for valor in valores_lista:
        try:
            float(valor)
        except ValueError:
            await interaction.followup.send(f"❌ Valor inválido: `{valor}`. Use números (ex: 5.50)", ephemeral=True)
            return
        
        valor_formatado = f"{float(valor):.2f}".replace(".", ",")
        
        fila_data = {
            "formato": formato,
            "tipo": tipo.value,
            "valor": valor_formatado,
            "jogadores": [],
        }
        
        embed = criar_embed_fila(formato, tipo.value, valor_formatado, [], guild_icon)
        view = FilaView(interaction.channel.id)
        
        msg = await interaction.channel.send(embed=embed, view=view)
        fila_data["msg_id"] = msg.id
        filas[f"{interaction.channel.id}_{msg.id}"] = fila_data
        view.channel_id = f"{interaction.channel.id}_{msg.id}"
    
    await interaction.followup.send(f"✅ {len(valores_lista)} fila(s) criada(s) com sucesso!", ephemeral=True)

# --- /painel ---
@bot.tree.command(name="painel", description="Configurar o bot no servidor")
async def painel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores!", ephemeral=True)
    
    guild_id = interaction.guild.id
    config = config_servidor.get(guild_id, {})
    
    embed = discord.Embed(
        title="⚙️ Painel de Configuração",
        description="Configure o bot para o seu servidor",
        color=EMBED_COLOR
    )
    
    cargo_mediador = config.get("cargo_mediador")
    canal_logs = config.get("canal_logs")
    categoria = config.get("categoria_apostas")
    cor = config.get("cor", EMBED_COLOR)
    
    embed.add_field(
        name="👤 Cargo Mediador",
        value=f"<@&{cargo_mediador}>" if cargo_mediador else "❌ Não definido",
        inline=True
    )
    embed.add_field(
        name="📋 Canal de Logs",
        value=f"<#{canal_logs}>" if canal_logs else "❌ Não definido",
        inline=True
    )
    embed.add_field(
        name="📁 Categoria Apostas",
        value=f"Definida" if categoria else "❌ Não definida",
        inline=True
    )
    embed.add_field(
        name="🎨 Cor do Embed",
        value=f"#{cor:06X}",
        inline=True
    )
    
    view = PainelView(guild_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PainelView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Cargo Mediador", style=discord.ButtonStyle.secondary, emoji="👤")
    async def set_mediador(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CargoMediadorModal(self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Canal de Logs", style=discord.ButtonStyle.secondary, emoji="📋")
    async def set_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CanalLogsModal(self.guild_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cor do Embed", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def set_cor(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CorModal(self.guild_id)
        await interaction.response.send_modal(modal)

class CargoMediadorModal(discord.ui.Modal, title="Definir Cargo Mediador"):
    cargo_id = discord.ui.TextInput(label="ID do Cargo Mediador", placeholder="Ex: 1234567890")
    
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.cargo_id.value)
            if self.guild_id not in config_servidor:
                config_servidor[self.guild_id] = {}
            config_servidor[self.guild_id]["cargo_mediador"] = cid
            await interaction.response.send_message(f"✅ Cargo mediador definido para <@&{cid}>!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)

class CanalLogsModal(discord.ui.Modal, title="Definir Canal de Logs"):
    canal_id = discord.ui.TextInput(label="ID do Canal de Logs", placeholder="Ex: 1234567890")
    
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.canal_id.value)
            if self.guild_id not in config_servidor:
                config_servidor[self.guild_id] = {}
            config_servidor[self.guild_id]["canal_logs"] = cid
            await interaction.response.send_message(f"✅ Canal de logs definido para <#{cid}>!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)

class CorModal(discord.ui.Modal, title="Alterar Cor do Embed"):
    cor_hex = discord.ui.TextInput(label="Cor em HEX (sem #)", placeholder="Ex: FF0000 (vermelho)")
    
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cor = int(self.cor_hex.value, 16)
            if self.guild_id not in config_servidor:
                config_servidor[self.guild_id] = {}
            config_servidor[self.guild_id]["cor"] = cor
            global EMBED_COLOR
            EMBED_COLOR = cor
            await interaction.response.send_message(f"✅ Cor alterada para `#{self.cor_hex.value}`!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Cor inválida! Use formato HEX (ex: FF0000)", ephemeral=True)

# --- /mediador ---
@bot.tree.command(name="mediador", description="Configurar fila de mediadores")
@app_commands.describe(acao="Ação a realizar")
@app_commands.choices(acao=[
    app_commands.Choice(name="Configurar fila", value="configurar"),
    app_commands.Choice(name="Gerenciar - Remover todos", value="remover"),
])
async def mediador(interaction: discord.Interaction, acao: app_commands.Choice[str]):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Apenas administradores!", ephemeral=True)
    
    if acao.value == "configurar":
        embed = discord.Embed(
            title="👥 Fila de Mediadores",
            description="Mediadores disponíveis para mediar apostas",
            color=EMBED_COLOR
        )
        
        if mediadores_fila:
            med_text = "\n".join([f"<@{m}>" for m in mediadores_fila])
        else:
            med_text = "Nenhum mediador na fila..."
        
        embed.add_field(name="Mediadores Online", value=med_text, inline=False)
        
        view = MediadorView()
        await interaction.response.send_message(embed=embed, view=view)
    
    elif acao.value == "remover":
        mediadores_fila.clear()
        await interaction.response.send_message("✅ Todos os mediadores foram removidos da fila!", ephemeral=True)

class MediadorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar na fila", style=discord.ButtonStyle.green, emoji="✅")
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild.id
        config = config_servidor.get(guild_id, {})
        cargo_id = config.get("cargo_mediador")
        
        if cargo_id:
            role = interaction.guild.get_role(cargo_id)
            if role and role not in interaction.user.roles:
                return await interaction.response.send_message("❌ Você precisa do cargo de mediador!", ephemeral=True)
        
        if interaction.user.id in mediadores_fila:
            return await interaction.response.send_message("⚠️ Você já está na fila!", ephemeral=True)
        
        mediadores_fila.append(interaction.user.id)
        
        embed = interaction.message.embeds[0]
        med_text = "\n".join([f"<@{m}>" for m in mediadores_fila])
        embed.set_field_at(0, name="Mediadores Online", value=med_text, inline=False)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você entrou na fila de mediadores!", ephemeral=True)

    @discord.ui.button(label="Sair da fila", style=discord.ButtonStyle.red, emoji="❌")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in mediadores_fila:
            return await interaction.response.send_message("⚠️ Você não está na fila!", ephemeral=True)
        
        mediadores_fila.remove(interaction.user.id)
        
        embed = interaction.message.embeds[0]
        if mediadores_fila:
            med_text = "\n".join([f"<@{m}>" for m in mediadores_fila])
        else:
            med_text = "Nenhum mediador na fila..."
        embed.set_field_at(0, name="Mediadores Online", value=med_text, inline=False)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Você saiu da fila de mediadores!", ephemeral=True)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        if mediadores_fila:
            med_text = "\n".join([f"<@{m}>" for m in mediadores_fila])
        else:
            med_text = "Nenhum mediador na fila..."
        embed.set_field_at(0, name="Mediadores Online", value=med_text, inline=False)
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("🔄 Atualizado!", ephemeral=True)

# --- /saldo ---
@bot.tree.command(name="saldo", description="Ver seu saldo de moedas")
async def saldo(interaction: discord.Interaction):
    user_id = interaction.user.id
    valor = saldos.get(user_id, 0.0)
    
    embed = discord.Embed(
        title="💰 Saldo",
        description=f"**Jogador:** {interaction.user.mention}\n**Saldo:** R$ {valor:.2f}",
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== INICIALIZAÇÃO ==========
if __name__ 
