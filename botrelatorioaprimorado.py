import discord
from discord.ext import commands
from discord.ui import Select, View, Modal, TextInput
from datetime import datetime
import datetime
from dotenv import load_dotenv
import os

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração das intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

# Inicialização do bot
bot = commands.Bot(command_prefix="!", intents=intents)

# ID do canal para enviar o relatório
relatorio_channel_id = 1354176886074249315

# Variáveis para armazenar informações temporárias do relatório
report_data = {}

# Listas de tipos de operação, missões e notas
operation_types = ["Intervenção Policial", "Operação Tática da SWAT", "Operação Integrada"]
missions = [
    "Obrigado, Volte Sempre", "Confins da Terra", "A Aranha", "Tumba de Neon", "Nervo Torcido",
    "Elefante", "Mãos Molhadas", "23 Megabytes por Segundo", "Vale das Bonecas",
    "Compra Barato, Compra Duas Vezes", "Dormitórios", "Narcos", "Recaída",
    "Em Meio às Videiras", "Uma Obsessão Letal", "Idos de Março", "Pecados do Pai",
    "Cinturão da Ferrugem", "Trilha Sinuosa", "Esconde-Esconde", "Legislador",
    "Miragens no Mar", "Leviathan", "Tríade de 3 Letras",
]
grades = ["S", "A+", "A", "B", "C", "D", "E", "F"]

# Classe para o menu de seleção do tipo de operação
class OperationTypeSelect(Select):
    def __init__(self):
        options = [discord.SelectOption(label=type_, value=type_) for type_ in operation_types]
        super().__init__(placeholder="Selecione o tipo de operação", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_type = self.values[0]
        report_data["operation_type"] = selected_type

        # Avança para a seleção do líder
        await interaction.response.edit_message(
            content=f"Tipo de operação selecionado: {selected_type}. Agora selecione o líder:",
            view=LeaderSelectView(interaction.guild.members)
        )

# Classe para criar a interface de seleção do tipo de operação
class SelectOperationTypeView(View):
    def __init__(self):
        super().__init__()
        self.add_item(OperationTypeSelect())

# Classe para o menu de seleção do líder
class LeaderSelect(Select):
    def __init__(self, members):
        options = [discord.SelectOption(label=member.display_name, value=str(member.id)) for member in members]
        super().__init__(placeholder="Selecione o líder da operação", options=options)

    async def callback(self, interaction: discord.Interaction):
        leader_id = self.values[0]
        leader_name = next(
            (member.display_name for member in interaction.guild.members if str(member.id) == leader_id),
            "Desconhecido"
        )
        report_data["leader"] = leader_id

        # Avança para a seleção do efetivo
        await interaction.response.edit_message(
            content=f"Líder escolhido: {leader_name}. Agora selecione o efetivo:",
            view=EffectiveSelectView(interaction.guild.members, leader_id)
        )

# Classe para criar a interface de seleção do líder
class LeaderSelectView(View):
    def __init__(self, members):
        super().__init__()
        self.add_item(LeaderSelect(members))

# Classe para o menu de seleção do efetivo
class EffectiveSelect(Select):
    def __init__(self, members, leader_id):
        options = [
            discord.SelectOption(
                label=member.display_name,
                value=str(member.id),
                description=f"ID: {member.id}",
                emoji=None,
                default=False
            )
            for member in members if str(member.id) != leader_id
        ]
        super().__init__(placeholder="Selecione o efetivo da operação", options=options, max_values=10)

        self.leader_id = leader_id

    async def callback(self, interaction: discord.Interaction):
        selected_ids = self.values + [self.leader_id]
        selected_names = [
            next(member.display_name for member in interaction.guild.members if str(member.id) == selected_id)
            for selected_id in selected_ids
        ]
        report_data["effective"] = selected_ids

        # Avança para a seleção da missão
        await interaction.response.edit_message(
            content=f"Efetivo escolhido: {', '.join(selected_names)}. Agora selecione a missão:",
            view=MissionSelectView()
        )

# Classe para criar a interface de seleção do efetivo
class EffectiveSelectView(View):
    def __init__(self, members, leader_id):
        super().__init__()
        self.add_item(EffectiveSelect(members, leader_id))

# Classe para o menu de seleção da missão
class MissionSelect(Select):
    def __init__(self):
        options = [discord.SelectOption(label=mission, value=mission) for mission in missions]
        super().__init__(placeholder="Selecione a missão da operação", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_mission = self.values[0]
        report_data["mission"] = selected_mission

        # Avança para a seleção da nota
        await interaction.response.edit_message(
            content=f"Missão escolhida: {selected_mission}. Agora selecione a nota:",
            view=GradeSelectView()
        )

# Classe para criar a interface de seleção da missão
class MissionSelectView(View):
    def __init__(self):
        super().__init__()
        self.add_item(MissionSelect())

# Classe para o menu de seleção da nota
class GradeSelect(Select):
    def __init__(self):
        options = [discord.SelectOption(label=grade, value=grade) for grade in grades]
        super().__init__(placeholder="Selecione a nota da operação", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_grade = self.values[0]
        report_data["grade"] = selected_grade

        # Abre o modal para o resumo da operação
        await interaction.response.send_modal(OperationSummaryModal())

# Classe para criar a interface de seleção da nota
class GradeSelectView(View):
    def __init__(self):
        super().__init__()
        self.add_item(GradeSelect())

# Classe para o modal de resumo da operação
class OperationSummaryModal(Modal, title="Resumo da Operação"):
    def __init__(self):
        super().__init__(timeout=None)
        self.summary = TextInput(label="Resumo da Operação", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.summary)

    async def on_submit(self, interaction: discord.Interaction):
        report_data["summary"] = self.summary.value
        await self.send_report(interaction)

    async def send_report(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="Relatório de Operação",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.add_field(name="Tipo de Operação", value=report_data["operation_type"], inline=False)
            embed.add_field(name="Líder", value=interaction.guild.get_member(int(report_data["leader"])).mention, inline=False)

            # Buscar membros da equipe pelo ID e formatar menções
            team_mentions = []
            for member_id in report_data["effective"]:
                member = interaction.guild.get_member(int(member_id))
                if member:
                    team_mentions.append(member.mention)
                else:
                    team_mentions.append(f"Membro {member_id} não encontrado") # Mensagem de erro caso o membro não seja encontrado

            embed.add_field(name="Equipe", value=", ".join(team_mentions), inline=False)
            embed.add_field(name="Missão", value=report_data["mission"], inline=False)
            embed.add_field(name="Nota", value=report_data["grade"], inline=False)
            embed.add_field(name="Resumo", value=report_data["summary"], inline=False)

            channel = bot.get_channel(relatorio_channel_id)
            if channel is None:
                raise ValueError(f"Canal com ID {relatorio_channel_id} não encontrado.")

            await channel.send(embed=embed)
            await interaction.response.send_message("Relatório enviado com sucesso!", ephemeral=True)
        except discord.Forbidden:
            print(f"Erro ao enviar relatório: Permissão negada no canal {relatorio_channel_id}")
            await interaction.response.send_message("Não tenho permissão para enviar mensagens neste canal.", ephemeral=True)
        except ValueError as e:
            print(f"Erro ao enviar relatório: {e}")
            await interaction.response.send_message("Ocorreu um erro ao encontrar o canal. Verifique o ID do canal.", ephemeral=True)
        except Exception as e:
            print(f"Erro ao enviar relatório: {e}")
            await interaction.response.send_message("Ocorreu um erro ao enviar o relatório. Por favor, tente novamente.", ephemeral=True)

# Comando para iniciar o relatório
@bot.tree.command(name="relatorio", description="Inicia o registro de um relatório de operação")
async def relatorio(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("Selecione o tipo de operação:", view=SelectOperationTypeView(), ephemeral=True)

# Evento para inicializar o bot
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"Bot conectado como {bot.user}")
        print("Comandos de barra sincronizados com sucesso!")
    except Exception as e:
        print(f"Erro ao sincronizar comandos de barra: {e}")

# Substitua "SEU_TOKEN_AQUI" pelo token do seu bot
bot.run(os.getenv("DISCORD_TOKEN_RELATORIO"))
