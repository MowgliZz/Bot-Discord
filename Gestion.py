import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
import requests
import json
from collections import defaultdict
import asyncio
import time
import io
from datetime import datetime, timedelta
import aiofiles
import os
from datetime import datetime, timezone  
intents = discord.Intents.default()
intents.members = True
intents.members = True
intents.voice_states = True
intents.message_content = True

with open(r"C:\Users\PC\Desktop\ㅤ\T2L\config.json", "r", encoding="utf-8") as f:
    config = json.load(f)




raidlist = []  # Liste des utilisateurs détectés en raid
message_logs = {} 
mention_logs = {}  
last_executions = {} 



bot = commands.Bot(command_prefix="!", intents=intents)

# ID autorisé à utiliser le bot (remplace ceci par l'ID de la personne autorisée)
OWNERS_IDS = [1158001764721774623]
SERVER_ID = 1284587381818785926
ALLOWED_CATEGORIES = [1338455637704708126, 1284587381818785928]

WEBHOOK_URL = "https://discord.com/api/webhooks/1358736081159196722/VqNGjRMiGr-oOd5hzdB3du_cBm-E53gkyfTh0pyT5pCrzsXrVHMIbC4JyhuInkvYn6YM"


# Fonction pour envoyer un message au webhook
def send_webhook_message(content):
    data = {
        "content": content
    }
    requests.post(WEBHOOK_URL, json=data)

blacklist = set()

## Fonction pour vérifier si la personne est autorisée
def is_owner(ctx):
    return ctx.author.id in OWNERS_IDS

# Fonction pour envoyer un message en embed
async def send_embed(ctx, title, description, color):
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)



# -------------------------------------------------- Fonction pour envoyer des embeds --------------------------------------------------
async def send_embed(ctx, title, description, color):
    embed = discord.Embed(title=title, description=description, color=color)
    await ctx.send(embed=embed)

# -------------------------------------------------- Commande pour bannir un membre --------------------------------------------------
executing_commands = set()

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: str, *, reason: str = "Aucune raison spécifiée."):
    """Bannit un membre et l'ajoute à la blacklist avec notification et protection contre les doublons."""

    if ctx.command.name in executing_commands:
        return  # Ignore la commande si elle est déjà en cours

    executing_commands.add(ctx.command.name)

    try:
        # 🔄 Convertir l'argument en membre
        member_converter = commands.MemberConverter()
        try:
            member = await member_converter.convert(ctx, member)
        except commands.MemberNotFound:
            await send_embed(ctx, "Erreur", "Membre introuvable. Vérifiez l'ID ou la mention.", discord.Color.orange())
            return

        # 🔒 Vérifications avant le ban
        if ctx.author.id not in OWNERS_IDS:
            await send_embed(ctx, "Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
            return

        if ctx.guild.owner_id == member.id or ctx.author.top_role <= member.top_role:
            await send_embed(ctx, "Erreur", "Vous ne pouvez pas bannir ce membre.", discord.Color.orange())
            return

        # 📨 Message privé au membre avant le bannissement
        embed = discord.Embed(
            title="🚫 Vous avez été banni",
            description=f"**Serveur :** {ctx.guild.name}\n**Sanction :** Bannissement\n**Raison :** {reason}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Modérateur : {ctx.author}")

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass  # Impossible d'envoyer un MP

        # 🚨 Bannir le membre
        await member.ban(reason=reason)

        # 🔔 Message de confirmation
        await send_embed(ctx, "🚨 Bannissement", f"{member.mention} a été **banni** avec succès.\n**Raison :** {reason}", discord.Color.red())

    except discord.Forbidden:
        await send_embed(ctx, "Erreur", "Je n'ai pas la permission de bannir ce membre.", discord.Color.orange())
    except Exception as e:
        await send_embed(ctx, "Erreur", f"Une erreur est survenue : {e}", discord.Color.orange())
    finally:
        executing_commands.discard(ctx.command.name)


# -------------------------------------------------- Commande pour débannir un membre --------------------------------------------------

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    """Débannit un membre."""

    if ctx.author.id not in OWNERS_IDS:
        await send_embed(ctx, "🚫 Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
        return

    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)

        try:
            dm_embed = discord.Embed(
                title="🔓 Vous avez été débanni !",
                description=(
                    f"**Serveur :** {ctx.guild.name}\n"
                    f"**Débanni par :** {ctx.author.mention}\n\n"
                    "Vous pouvez maintenant rejoindre à nouveau le serveur."
                ),
                color=discord.Color.green()
            )
            # Ajout du lien du serveur
            dm_embed.add_field(
                name="🔗 Rejoindre le serveur",
                value="[Clique ici pour rejoindre](https://discord.gg/wJmv9xGZRQ)",
                inline=False
            )

            await user.send(embed=dm_embed)
        except discord.Forbidden:
            await ctx.send(f"⚠️ Impossible d'envoyer un MP à {user.mention}.")

        await send_embed(ctx, "✅ Débannissement", f"{user.mention} a été **débanni** avec succès.", discord.Color.green())

    except discord.NotFound:
        await send_embed(ctx, "❌ Erreur", "Aucun utilisateur trouvé avec cet ID.", discord.Color.red())

#---------------------------------------------------commands clear
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: str):  # Change `amount` en `str` pour accepter "all"
    if ctx.author.id not in OWNERS_IDS:
        await send_embed(ctx, "Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
        return

    # Vérifie si l'utilisateur veut supprimer tous les messages
    if amount.lower() == "all":
        # Envoi de l'action dans le webhook avant de purger les messages
        send_webhook_message(f"{ctx.author} a clear tous les messages dans le salon {ctx.channel.name}.")
        
        # Purger tous les messages (limite de 100 pour chaque purge)
        await ctx.channel.purge(limit=None)  # Supprime tous les messages

        # Confirmation de la suppression
        await ctx.send("Tous les messages ont été supprimés.", delete_after=5)
    else:
        try:
            amount = int(amount)  # Convertir en entier si ce n'est pas "all"
        except ValueError:
            await send_embed(ctx, "Erreur", "Veuillez spécifier un nombre valide ou 'all'.", discord.Color.red())
            return
        
        # Envoi de l'action dans le webhook avant de purger les messages
        send_webhook_message(f"{ctx.author} a clear {amount} messages dans le salon {ctx.channel.name}.")
        
        # Purger les messages
        await ctx.channel.purge(limit=amount + 1)

        # Confirmation du nombre de messages supprimés
        await ctx.send(f"{amount} messages supprimés.", delete_after=5)


#--------------------------------------------------- Commande +BL


# ID du rôle à ajouter
ROLE_TO_ADD = 1329924546467205192

@bot.command()
@commands.has_permissions(manage_roles=True)
async def bl(ctx, member: discord.Member):
    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("Accès refusé : vous n'êtes pas autorisé à utiliser cette commande.")
        return
    """
    Retire tous les rôles d'un membre et lui ajoute uniquement le rôle spécifié par ROLE_TO_ADD.
    """
    role_to_add = ctx.guild.get_role(ROLE_TO_ADD)
    if not role_to_add:
        await ctx.send("⚠️ Le rôle spécifié n'a pas été trouvé sur ce serveur.")
        return

    try:
        # Retirer tous les rôles du membre
        await member.edit(roles=[role_to_add])
        await ctx.send(f"✅ L'utilisateur à été Blacklist")
    except discord.Forbidden:
        await ctx.send("⚠️ Je n'ai pas la permission de gérer les rôles pour cet utilisateur.")
    except Exception as e:
        await ctx.send("⚠️ Une erreur est survenue.")
        print(f"Erreur lors de la modification des rôles : {e}")

#--------------------------------------------------- Commande +UNBL
# ID du rôle "BL" à retirer
ROLE_BL_ID = 1329924546467205192
# ID du rôle à ajouter
ROLE_TO_ADD_ID = 1356651241706623046



@bot.command()
@commands.has_permissions(manage_roles=True)
async def unbl(ctx, member: discord.Member):
    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("Accès refusé : vous n'êtes pas autorisé à utiliser cette commande.")
        return
    """
    Retire le rôle "BL" d'un membre et lui ajoute le rôle spécifié par ROLE_TO_ADD_ID.
    """
    role_bl = ctx.guild.get_role(ROLE_BL_ID)
    role_to_add = ctx.guild.get_role(ROLE_TO_ADD_ID)
    
    if not role_bl:
        await ctx.send("⚠️ Le rôle 'BL' spécifié n'a pas été trouvé sur ce serveur.")
        return
    
    if not role_to_add:
        await ctx.send("⚠️ Le rôle à ajouter n'a pas été trouvé sur ce serveur.")
        return

    try:
        # Retirer le rôle "BL"
        if role_bl in member.roles:
            await member.remove_roles(role_bl)
        
        # Ajouter le rôle spécifié
        await member.add_roles(role_to_add)
        await ctx.send(f"✅ L'utilisateur à été Unblacklist")
    except discord.Forbidden:
        await ctx.send("⚠️ Je n'ai pas la permission de gérer les rôles pour cet utilisateur.")
    except Exception as e:
        await ctx.send("⚠️ Une erreur est survenue.")
        print(f"Erreur lors de la gestion des rôles : {e}")

# ---------------------------------------------------Commande pour verrouiller un salon

# Liste des IDs des rôles à modifier
ROLES_TO_MODIFY = [1252955535901200415, 1356651241706623046, 1252955309698191433]

@bot.command()
async def lock(ctx):
    """
    Retire uniquement la permission d'envoyer des messages dans le salon actuel pour les rôles
    spécifiés dans ROLES_TO_MODIFY, sans modifier les autres permissions.
    """
    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("⚠️ Accès refusé : vous n'êtes pas autorisé à utiliser cette commande.")
        return

    modified_roles = []
    for role_id in ROLES_TO_MODIFY:
        role = ctx.guild.get_role(role_id)
        if not role:
            continue

        # Récupère l'override existant pour ce rôle sur le canal
        current_overwrite = ctx.channel.overwrites_for(role)
        # Assure-toi de ne toucher qu'à la permission "send_messages"
        current_overwrite.update(send_messages=False)

        try:
            await ctx.channel.set_permissions(role, overwrite=current_overwrite)
            modified_roles.append(role.name)
        except Exception as e:
            print(f"Erreur lors de la modification pour le rôle {role.name} : {e}")

    if modified_roles:
        await ctx.send(f"🔒 Salon verrouillé !")
    else:
        await ctx.send("⚠️ Aucun rôle n'a été modifié.")

@bot.command()
async def unlock(ctx):
    """
    Rétablit uniquement la permission d'envoyer des messages dans le salon actuel pour les rôles
    spécifiés dans ROLES_TO_MODIFY, sans toucher aux autres permissions.
    """
    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("⚠️ Accès refusé : vous n'êtes pas autorisé à utiliser cette commande.")
        return

    modified_roles = []
    for role_id in ROLES_TO_MODIFY:
        role = ctx.guild.get_role(role_id)
        if not role:
            continue

        # Récupère l'override existant pour ce rôle sur le canal
        current_overwrite = ctx.channel.overwrites_for(role)
        # Rétablit uniquement la permission "send_messages" à son état par défaut
        current_overwrite.update(send_messages=None)

        try:
            await ctx.channel.set_permissions(role, overwrite=current_overwrite)
            modified_roles.append(role.name)
        except Exception as e:
            print(f"Erreur lors de la modification pour le rôle {role.name} : {e}")

    if modified_roles:
        await ctx.send(f"🔓 Salon déverrouillé !")
    else:
        await ctx.send("⚠️ Aucun rôle n'a été modifié.")


#--------------------------------------------------- COMMANDS EMBED
COLOR_OPTIONS = [
    discord.SelectOption(label="Rouge", value="red"),
    discord.SelectOption(label="Vert", value="green"),
    discord.SelectOption(label="Bleu", value="blue"),
    discord.SelectOption(label="Orange", value="orange"),
    discord.SelectOption(label="Violet", value="purple"),
]

# Dictionnaire de conversion des couleurs
COLOR_MAP = {
    "red": discord.Color.red(),
    "green": discord.Color.green(),
    "blue": discord.Color.blue(),
    "orange": discord.Color.orange(),
    "purple": discord.Color.purple(),
}

class EmbedFormModal(discord.ui.Modal, title="Créer un Embed"):
    def __init__(self, color, user):
        super().__init__()
        self.color = color
        self.user = user

        self.title_input = discord.ui.TextInput(label="Titre de l'embed", placeholder="Entrez le titre ici", required=True)
        self.description_input = discord.ui.TextInput(label="Description de l'embed", placeholder="Entrez la description ici", required=True, style=discord.TextStyle.long)

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.title_input.value,
            description=self.description_input.value,
            color=self.color
        )

        # Afficher le menu pour choisir un salon
        view = SelectChannelView(embed, self.user)
        await interaction.response.send_message("Sélectionnez le salon où envoyer l'embed :", view=view, ephemeral=True)

class SelectChannelDropdown(discord.ui.Select):
    def __init__(self, embed, user):
        self.embed = embed
        self.user = user

        # Filtrer les salons où l'utilisateur peut envoyer des messages
        channels = [channel for channel in user.guild.text_channels if channel.permissions_for(user).send_messages]
        
        if not channels:
            raise ValueError("Aucun salon disponible pour envoyer un embed.")

        options = [
            discord.SelectOption(label=channel.name[:25], value=str(channel.id))
            for channel in channels[:25]  # Discord accepte max 25 options
        ]

        super().__init__(placeholder="Choisissez un salon...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("⚠️ Vous ne pouvez pas utiliser cette sélection.", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(int(self.values[0]))
        if channel:
            await channel.send(embed=self.embed)
            await interaction.response.send_message(f"✅ Embed envoyé dans {channel.mention} !", ephemeral=True)

class SelectChannelView(discord.ui.View):
    def __init__(self, embed, user):
        super().__init__()
        self.add_item(SelectChannelDropdown(embed, user))

class EmbedCreatorView(discord.ui.View):
    def __init__(self):
        super().__init__()

        self.color_selector = discord.ui.Select(
            placeholder="Choisissez la couleur de l'embed...",
            options=COLOR_OPTIONS
        )
        self.color_selector.callback = self.color_selected
        self.add_item(self.color_selector)

        self.color = None  # Couleur sélectionnée

    async def color_selected(self, interaction: discord.Interaction):
        self.color = COLOR_MAP.get(self.color_selector.values[0], discord.Color.blue())
        await interaction.response.send_message("✅ Couleur sélectionnée. Appuyez sur **Créer l'embed**.", ephemeral=True)

    @discord.ui.button(label="Créer l'embed", style=discord.ButtonStyle.green)
    async def create_embed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.color is None:
            await interaction.response.send_message("⚠️ Veuillez d'abord sélectionner une couleur.", ephemeral=True)
            return
        
        await interaction.response.send_modal(EmbedFormModal(color=self.color, user=interaction.user))

@bot.command()
async def embed(ctx):
    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("⛔ Vous n'êtes pas autorisé à utiliser cette commande.", delete_after=5)
        return

    view = EmbedCreatorView()
    await ctx.send("Veuillez choisir une couleur puis créer votre embed :", view=view)



# commands warn
@bot.command()
async def warn(ctx, member: discord.Member, *, reason="Aucune raison spécifiée"):
    warn_role_id = 1346521174494019676  # Remplace par l'ID du rôle de sanction

    # Vérification des permissions : Seuls les owners définis peuvent exécuter la commande
    if ctx.author.id not in OWNERS_IDS:
        await send_embed(ctx, "🚫 Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
        return

    # Vérifier si le rôle existe
    warn_role = ctx.guild.get_role(warn_role_id)
    if not warn_role:
        await send_embed(ctx, "⚠️ Erreur", "Le rôle de sanction n'existe pas. Vérifiez l'ID.", discord.Color.orange())
        return

    # Ajouter le rôle au membre averti
    await member.add_roles(warn_role, reason=f"Warn par {ctx.author} : {reason}")

    # Envoyer un message dans le salon
    await send_embed(ctx, "⚠️ WARN ⚠️", f"{member.mention} a été averti par {ctx.author.mention}.\n\nRaison : {reason}", discord.Color.orange())

    # Envoyer un message en MP au membre averti
    try:
        dm_embed = discord.Embed(
            title="⚠️ Vous avez été WARN ⚠️",
            description=f"Serveur : {ctx.guild.name}\nAverti par : {ctx.author.mention}\n\nRaison : {reason}",
            color=discord.Color.red()
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        await ctx.send(f"⚠️ Impossible d'envoyer un MP à {member.mention}.")

    # Envoyer un log via le webhook
    send_webhook_message(f"📢 {member} a été averti par {ctx.author}.\n🔹 Raison : {reason}")


#-----------------------------------------------------Commande +role---------------------------------------------------

ROLE_ID = 1252955535901200415  # ID du rôle de recrutement

@bot.command()
async def role(ctx):
    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("❌ Vous n'avez pas la permission d'utiliser cette commande.")
        return
    
    embed = discord.Embed(
        title="📢 Accès au recrutement !",
        description="Tu souhaites te recruter et avoir accès aux canaux de recrutement ? C'est très simple !\n\n"
                    "✅ Clique sur la réaction verte pour obtenir le rôle Recrutement et accéder au canal.\n"
                    "❌ Clique sur la réaction rouge pour retirer le rôle et perdre l'accès.\n\n"
                    "🔑 Le rôle Recrutement te permet de :\n"
                    "🔹 Avoir accès aux discussions de recrutement.\n"
                    "🔹 Pouvoir se faire recruter.\n\n"
                    "⚠️ Remarque : Pour se faire recruter il est impératif d'avoir ce rôle !\n\n"
                    "🎯 Prêt à rejoindre l'équipe ? Réagis dès maintenant ! 🚀",
        color=discord.Color.green()
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

@bot.event
async def on_raw_reaction_add(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    role = guild.get_role(ROLE_ID)
    if not role:
        return
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return
    if str(payload.emoji) == "✅":
        await member.add_roles(role)
        await guild.system_channel.send(f"✅ {member.mention} a reçu le rôle Recrutement !")
    elif str(payload.emoji) == "❌":
        await member.remove_roles(role)
        await guild.system_channel.send(f"❌ {member.mention} a perdu le rôle Recrutement.")

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    role = guild.get_role(ROLE_ID)
    if not role:
        return
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return
    if str(payload.emoji) == "❌":  # Seul le bouton rouge retire le rôle
        await member.remove_roles(role)
        await guild.system_channel.send(f"❌ {member.mention} a perdu le rôle Recrutement.")

# ---------------------------------------------------Commande pour renommer un ticket
@bot.command()
@commands.has_permissions(manage_channels=True)
async def rename(ctx, new_name: str):
    if ctx.author.id not in OWNERS_IDS:  # Vérification de l'ID du propriétaire
        await send_embed(ctx, "Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
        return

    if "ticket-" in ctx.channel.name:
        await ctx.channel.edit(name=f"{new_name}")
        await send_embed(ctx, "Renommage du ticket", f"Ticket renommé en {new_name}.", discord.Color.green())
    else:
        await send_embed(ctx, "Erreur", "Vous ne pouvez pas renommer ce canal.", discord.Color.red())

# command renew
@bot.command()
@commands.has_permissions(manage_channels=True)
async def renew(ctx):
    if ctx.author.id not in OWNERS_IDS:
        await send_embed(ctx, "Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
        return

    # Récupérer le nom, la catégorie et la position du salon actuel
    channel_name = ctx.channel.name
    category = ctx.channel.category
    position = ctx.channel.position

    # Envoi d'un embed pour informer que le renouvellement va commencer
    await send_embed(ctx, "Renouvellement du salon", "Ce salon va être dupliqué et l'ancien sera supprimé.", discord.Color.blue())

    # Envoi du log dans le webhook
    send_webhook_message(f"{ctx.author} a dupliqué et renouvelé le salon : {channel_name}.")

    # Création du nouveau salon au même endroit et dans la même catégorie
    new_channel = await ctx.guild.create_text_channel(name=channel_name, category=category, position=position)

    # Copier les permissions du salon original au nouveau salon
    for role, overwrite in ctx.channel.overwrites.items():
        await new_channel.set_permissions(role, overwrite=overwrite)

    # Informer l'utilisateur dans le nouveau salon que c'est une duplication
    await new_channel.send(f"✅ Le salon a été renew par {ctx.author.mention}.")

    # Tentative de suppression de l'ancien salon
    try:
        await ctx.channel.delete()
        send_webhook_message(f"Le salon {channel_name} a été supprimé après duplication.")
    except discord.errors.HTTPException as e:
        if e.code == 50074:
            # Si l'erreur est liée à un salon requis, on envoie un message sans supprimer le salon
            send_webhook_message(f"Le salon {channel_name} n'a pas pu être supprimé car il est requis pour le serveur communautaire.")
            await ctx.send(f"Le salon {channel_name} ne peut pas être supprimé car il est requis pour le serveur communautaire.")
        else:
            # Autres erreurs HTTP
            raise e



# ---------------------------------------------------------------------------------------ticket


# Remplacez ces ID par ceux de votre serveur
CATEGORY_TICKET1 = 1345828022736912416  # ID de la catégorie pour ticket général
CATEGORY_TICKET2 = 1345828647671693355  # ID de la catégorie pour ticket recrutement
CATEGORY_TICKET3 = 1345828647671693355  # ID de la catégorie pour ticket statistiques
LOG_CHANNEL_ID = 1357085222616825979   # ID du salon de log

# Dictionnaire pour stocker le nombre total de tickets par utilisateur
user_ticket_count = {}

# Modal pour fermer un ticket avec une raison
class CloseTicketModal(Modal):
    def __init__(self, channel: discord.TextChannel, opener_name: str, opener_id: int):
        self.channel = channel
        self.opener_name = opener_name
        self.opener_id = opener_id
        super().__init__(title="Raison de fermeture du ticket")

        self.reason = TextInput(
            label="Raison",
            placeholder="Fournissez une raison pour fermer ce ticket",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        # Déférer la réponse pour éviter un timeout
        await interaction.response.defer()
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        # Générer la transcription sous forme de discord.File via un buffer en mémoire
        transcript = await self.generate_transcript(self.channel)

        # Limiter la longueur de la raison aux limites autorisées pour un embed
        reason_text = self.reason.value
        if len(reason_text) > 1024:
            reason_text = reason_text[:1021] + "..."

        # Créer l'embed de log
        embed = discord.Embed(
            title="🗒️ Ticket fermé",
            description=f"Le ticket **{self.channel.name}** a été fermé.",
            color=discord.Color.red()
        )
        embed.add_field(name="Ouvert par", value=f"{self.opener_name} (`{self.opener_id}`)", inline=False)
        embed.add_field(name="Fermé par", value=interaction.user.mention, inline=False)
        embed.add_field(name="Raison", value=reason_text, inline=False)
        embed.add_field(name="Date et Heure", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.set_footer(text="Système de gestion de ticket")

        if log_channel:
            try:
                await log_channel.send(embed=embed, file=transcript)
            except Exception as e:
                print(f"Erreur lors de l'envoi du log : {e}")

        try:
            await self.channel.delete()
        except Exception as e:
            print(f"Erreur lors de la suppression du canal : {e}")

        # Décrémente le compteur de ticket de l'utilisateur
        if self.opener_id in user_ticket_count:
            user_ticket_count[self.opener_id] = max(user_ticket_count[self.opener_id] - 1, 0)

    async def generate_transcript(self, channel: discord.TextChannel) -> discord.File:
        """Génère une transcription des messages du ticket."""
        messages = []
        async for message in channel.history(limit=None):
            messages.append(message)

        transcript_stream = io.StringIO()
        # Parcourt les messages dans l'ordre chronologique
        for message in reversed(messages):
            transcript_stream.write(f"{message.created_at} - {message.author}: {message.content}\n")
        transcript_stream.seek(0)

        # Créer un objet discord.File en utilisant un buffer BytesIO
        transcript_bytes = io.BytesIO(transcript_stream.getvalue().encode('utf-8'))
        return discord.File(transcript_bytes, filename=f"{channel.name}_transcript.txt")

# Vue pour le bouton de fermeture de ticket
class CloseTicketView(View):
    def __init__(self, opener_name: str, opener_id: int):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton(opener_name, opener_id))

class CloseTicketButton(Button):
    def __init__(self, opener_name: str, opener_id: int):
        super().__init__(label="❌ Fermer le Ticket", style=discord.ButtonStyle.danger)
        self.opener_name = opener_name
        self.opener_id = opener_id

    async def callback(self, interaction: discord.Interaction):
        modal = CloseTicketModal(interaction.channel, self.opener_name, self.opener_id)
        await interaction.response.send_modal(modal)

# Vue pour créer des tickets
class TicketView(View):
    def __init__(self, category_id: int):
        super().__init__(timeout=None)
        self.category_id = category_id

    @discord.ui.button(label="🎟️ Ouvrir Ticket", style=discord.ButtonStyle.primary)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("⚠️ Cette commande ne peut être utilisée que sur un serveur.", ephemeral=True)
            return

        user_id = interaction.user.id

        # Vérifier que l'utilisateur n'a pas dépassé le nombre maximum de 3 tickets
        if user_ticket_count.get(user_id, 0) >= 3:
            await interaction.response.send_message("⚠️ Vous avez déjà atteint le maximum de 3 tickets.", ephemeral=True)
            return

        category = guild.get_channel(self.category_id)
        if isinstance(category, discord.CategoryChannel):
            try:
                ticket_channel = await category.create_text_channel(f"ticket-{interaction.user.name}")
                await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
                
                embed = discord.Embed(
                    title="🎫 Ticket Ouvert",
                    description=f"Bonjour {interaction.user.mention}, votre ticket a été ouvert. Un membre du staff va vous assister sous peu.",
                    color=discord.Color.green()
                )
                await ticket_channel.send(embed=embed, view=CloseTicketView(interaction.user.name, interaction.user.id))
                await interaction.response.send_message(f"✅ Votre ticket a été ouvert : {ticket_channel.mention}", ephemeral=True)
                
                # Incrémenter le nombre de tickets de l'utilisateur
                user_ticket_count[user_id] = user_ticket_count.get(user_id, 0) + 1
            except Exception as e:
                await interaction.response.send_message("⚠️ Une erreur est survenue lors de la création du ticket.", ephemeral=True)
                print(f"Erreur lors de la création du ticket : {e}")
        else:
            await interaction.response.send_message("⚠️ La catégorie de ticket spécifiée est introuvable ou incorrecte.", ephemeral=True)


# Commande pour créer le bouton de ticket général
@bot.command()
async def ticket1(ctx):
        # Vérification des permissions de l'utilisateur
    if ctx.author.id not in OWNERS_IDS:
        embed = discord.Embed(
            title="🚫 Accès refusé",
            description="Vous n'êtes pas autorisé à utiliser cette commande.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(
        title="🎫 Ticket Général",
        description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket général.",
        color=discord.Color.blue()
    )
    view = TicketView(CATEGORY_TICKET1)
    await ctx.send(embed=embed, view=view)

# Commande pour créer le bouton de ticket recrutement
@bot.command()
async def ticket2(ctx):
        # Vérification des permissions de l'utilisateur
    if ctx.author.id not in OWNERS_IDS:
        embed = discord.Embed(
            title="🚫 Accès refusé",
            description="Vous n'êtes pas autorisé à utiliser cette commande.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(
        title="📌 Ticket Recrutement",
        description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket de recrutement.",
        color=discord.Color.green()
    )
    view = TicketView(CATEGORY_TICKET2)
    await ctx.send(embed=embed, view=view)

# Commande pour créer le bouton de ticket statistiques
@bot.command()
async def ticket3(ctx):
        # Vérification des permissions de l'utilisateur
    if ctx.author.id not in OWNERS_IDS:
        embed = discord.Embed(
            title="🚫 Accès refusé",
            description="Vous n'êtes pas autorisé à utiliser cette commande.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    embed = discord.Embed(
        title="📊 Ticket Statistiques",
        description="Cliquez sur le bouton ci-dessous pour ouvrir un ticket de statistiques.",
        color=discord.Color.purple()
    )
    view = TicketView(CATEGORY_TICKET3)
    await ctx.send(embed=embed, view=view)

# Commande pour fermer un ticket via commande texte
@bot.command()
async def close(ctx):
    """Ferme un ticket via commande."""
        # Vérification des permissions de l'utilisateur
    if ctx.author.id not in OWNERS_IDS:
        embed = discord.Embed(
            title="🚫 Accès refusé",
            description="Vous n'êtes pas autorisé à utiliser cette commande.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    if ctx.channel.category is None or "ticket" not in ctx.channel.name:
        await ctx.send("⚠️ Cette commande doit être utilisée dans un canal de ticket.")
        return

    log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
    transcript = await generate_transcript(ctx.channel)

    embed = discord.Embed(
        title="🗒️ Ticket fermé",
        description=f"Le ticket **{ctx.channel.name}** a été fermé.",
        color=discord.Color.red()
    )
    # Extraction du nom de l'utilisateur à partir du nom du canal (ex: ticket-username)
    opener_username = ctx.channel.name.split('-')[1] if '-' in ctx.channel.name else "Inconnu"
    embed.add_field(name="Ouvert par", value=opener_username, inline=False)
    embed.add_field(name="Fermé par", value=ctx.author.mention, inline=False)
    embed.add_field(name="Raison", value="Fermé via commande", inline=False)
    embed.add_field(name="Date et Heure", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.set_footer(text="Système de gestion de ticket")

    if log_channel:
        try:
            await log_channel.send(embed=embed, file=transcript)
        except Exception as e:
            await ctx.send("⚠️ Une erreur est survenue lors de l'envoi du log.")
            print(f"Erreur lors de l'envoi du log : {e}")

    try:
        await ctx.channel.delete()
    except Exception as e:
        await ctx.send("⚠️ Une erreur est survenue lors de la suppression du canal.")
        print(f"Erreur lors de la suppression du canal : {e}")

    # Décrémente le nombre de tickets de l'utilisateur
    user_id = ctx.author.id
    if user_ticket_count.get(user_id, 0) > 0:
        user_ticket_count[user_id] = max(user_ticket_count[user_id] - 1, 0)

async def generate_transcript(channel: discord.TextChannel) -> discord.File:
    """Génère une transcription des messages du ticket."""
    messages = []
    async for message in channel.history(limit=None):
        messages.append(message)

    transcript_stream = io.StringIO()
    for message in reversed(messages):  # ordre chronologique
        transcript_stream.write(f"{message.created_at} - {message.author}: {message.content}\n")
    transcript_stream.seek(0)

    transcript_bytes = io.BytesIO(transcript_stream.getvalue().encode('utf-8'))
    return discord.File(transcript_bytes, filename=f"{channel.name}_transcript.txt")

#-------------------------------------------------Remove-------------------------------------------

@bot.command()
async def remove(ctx, member: discord.Member):
    """
    Retire un utilisateur d'un ticket.
    """
    # Vérification des permissions de l'utilisateur
    if ctx.author.id not in OWNERS_IDS:
        embed = discord.Embed(
            title="🚫 Accès refusé",
            description="Vous n'êtes pas autorisé à utiliser cette commande.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Vérification si la commande est exécutée dans un canal appartenant à une catégorie autorisée
    if ctx.channel.category and ctx.channel.category.id in ALLOWED_CATEGORIES:
        # Suppression des permissions de l'utilisateur pour ce canal
        await ctx.channel.set_permissions(member, read_messages=False, send_messages=False)

        embed = discord.Embed(
            title=" Suppression du membre",
            description=f"{member.mention} a été retiré du ticket.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Erreur",
            description="Cette commande doit être utilisée dans un ticket.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

#------------------------------------------------ADD

@bot.command()
async def add(ctx, member: discord.Member):
    """
    Ajoute un utilisateur à un ticket.
    """
    # Vérification des permissions de l'utilisateur exécutant la commande
    if ctx.author.id not in OWNERS_IDS:
        embed = discord.Embed(
            title="🚫 Accès refusé",
            description="Vous n'êtes pas autorisé à utiliser cette commande.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Vérification si la commande est exécutée dans un canal appartenant à une catégorie autorisée
    if ctx.channel.category and ctx.channel.category.id in ALLOWED_CATEGORIES:
        # Ajout des permissions de lecture et écriture pour le membre spécifié
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title="✅ Ajout d'un membre",
            description=f"{member.mention} a été ajouté au ticket.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Erreur",
            description="Cette commande doit être utilisée dans un ticket.",
            color=discord.Color.red()
        )
        
#-----------------------------------------------------------------------------------------Commande kick

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Aucune raison fournie"):
    """
    Expulse un membre du serveur.
    Usage: +kick @membre [raison]
    """
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} a été expulsé par {ctx.author.mention} pour la raison suivante : {reason}")
    except Exception as e:
        await ctx.send("Une erreur s'est produite lors de la tentative d'expulsion.")
        print(f"Erreur lors de l'expulsion : {e}")


# ----------------------------------------------------------------------------------------commands masssive role

async def callback(self, interaction: discord.Interaction):
    # Récupère l'ID du rôle sélectionné
    role_id = int(self.values[0])
    role = interaction.guild.get_role(role_id)
    if role:
        embed = discord.Embed(
            title="📢 Attribution massive de rôle en cours",
            description=f"Le rôle **{role.name}** est en train d'être attribué aux membres...",
            color=discord.Color.blue()
        )
        embed.add_field(name="Progression", value="0 membres traités...", inline=False)
        
        # Send the initial embed using followup and get the message object
        message = await interaction.followup.send(embed=embed, ephemeral=True)

        added_members = []  # Pour stocker les membres auxquels le rôle a été attribué
        failed_members = []  # Pour stocker les membres pour lesquels l'opération a échoué
        total_members = len(interaction.guild.members)
        processed_count = 0  # Compteur de progression

        for member in interaction.guild.members:
            processed_count += 1

            # Ignore les membres dans la whitelist
            if member.id in OWNERS_IDS:
                continue

            try:
                await member.add_roles(role)
                added_members.append(member.name)
            except discord.Forbidden:
                # Permissions insuffisantes pour attribuer le rôle à ce membre
                failed_members.append(member.name)
            except discord.HTTPException:
                # Erreur générique d'API Discord
                failed_members.append(member.name)

            # Mise à jour de l'embed
            embed.set_field_at(
                0,
                name="Progression",
                value=f"{processed_count}/{total_members} membres traités...",
                inline=False
            )
            await message.edit(embed=embed)  # Edit the message with updated progress

        # Réponses finales
        embed.title = "📢 Résultat de l'attribution massive"
        embed.description = f"Le rôle **{role.name}** a été attribué avec succès."
        embed.set_field_at(
            0,
            name="Progression",
            value=f"Traitement terminé : {processed_count}/{total_members} membres traités",
            inline=False
        )

        if added_members:
            embed.add_field(
                name="Succès",
                value=f"Le rôle a été attribué à : {', '.join(added_members)}",
                inline=False
            )
        if failed_members:
            embed.add_field(
                name="Échecs",
                value=f"Impossible d'attribuer le rôle à : {', '.join(failed_members)}",
                inline=False
            )

        await message.edit(embed=embed)  # Final update of the embed
    else:
        # Si le rôle n'est pas trouvé
        await interaction.response.send_message("⚠️ Rôle introuvable.", ephemeral=True)

# Commande say------------------------------------------------------------------------------------------------------------------------------------------

@bot.command()
async def say(ctx, *, message: str):
    """Le bot répète le message et supprime l'original, accessible uniquement aux propriétaires."""

    if ctx.author.id not in OWNERS_IDS:
        await ctx.send("⛔ Vous n'êtes pas autorisé à utiliser cette commande.", delete_after=5)
        return

    try:
        await ctx.message.delete()  # Supprime le message original
        await ctx.send(message)  # Envoie le message du bot
    except discord.Forbidden:
        await ctx.send("⚠️ Je n'ai pas la permission de supprimer le message.", delete_after=5)
    except Exception as e:
        await ctx.send(f"⚠️ Une erreur est survenue : {e}", delete_after=5)

# systeme arriver---------------------------------------------------------------------------------------------------------------------------------------

WELCOME_CHANNEL_ID = 1338454947552825355  # ID du salon de bienvenue

@bot.event
async def on_ready():
    print(f"✅ {bot.user} est prêt !")

@bot.event
async def on_member_join(member):
    """Envoie un message de bienvenue en embed lorsqu'un membre rejoint."""
    guild = member.guild
    welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
    
    if not welcome_channel:
        print("❌ Salon de bienvenue introuvable.")
        return

    # Calcul de l'âge du compte avec gestion des timezones
    now = datetime.now(timezone.utc)  # Convertir l'heure actuelle en UTC avec timezone
    account_age = (now - member.created_at).days
    creation_date = member.created_at.strftime("%d/%m/%Y à %H:%M:%S")

    # Création de l'embed
    embed = discord.Embed(
        title="👋 Bienvenue sur le serveur !",
        description=f"Salut {member.mention}, ravi de t'accueillir parmi nous ! 🎉",
        color=discord.Color.blue()
    )

    # Gestion de l'avatar
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    embed.set_thumbnail(url=avatar_url)

    embed.add_field(name="📅 Date de création du compte", value=f"{creation_date} (**{account_age} jours**)", inline=False)
    embed.add_field(name="👥 Membres sur le serveur", value=f"Nous sommes désormais **{guild.member_count}** !", inline=False)
    embed.set_footer(text=f"ID de l'utilisateur : {member.id}")

    # Envoi du message embed avec gestion des erreurs
    try:
        await welcome_channel.send(embed=embed)
    except discord.Forbidden:
        print("❌ Le bot n'a pas la permission d'envoyer un message dans le salon de bienvenue.")
    except discord.HTTPException as e:
        print(f"❌ Erreur lors de l'envoi du message de bienvenue : {e}")

#--------------------------------------------------- Commande pour voir les commandes disponibles-----------------------------------------------------------------------
@bot.command(name="aide")
async def aide(ctx):
    if not is_owner(ctx):  # Utiliser is_owner à la place de OWNERS_IDS(ctx)
        await send_embed(ctx, "Accès refusé", "Vous n'êtes pas autorisé à utiliser cette commande.", discord.Color.red())
        return
    embed = discord.Embed(title="Commandes du bot", description="Voici les commandes disponibles:")
    embed.add_field(name="+ban `id`", value="Bannir un membre", inline=False)
    embed.add_field(name="+unban `id`", value="Débannir un membre", inline=False)
    embed.add_field(name="+kick `id`", value="Expulser un membre", inline=False)
    embed.add_field(name="+rename", value="Renommer un ticket", inline=False)
    embed.add_field(name="+close", value="Fermer un ticket", inline=False)
    embed.add_field(name="+embed", value="Crée un embed", inline=False)
    embed.add_field(name="+bl`id`", value="Ajouter un membre à la blacklist", inline=False)
    embed.add_field(name="+unbl `id`", value="Retirer un membre de la blacklist", inline=False)
    embed.add_field(name="+clear `nombre`", value="Supprimer un certain nombre de messages", inline=False)
    embed.add_field(name="+lock", value="Verrouiller un salon", inline=False)
    embed.add_field(name="+unlock", value="Déverrouiller un salon", inline=False)
    embed.add_field(name="+renew", value="pour refaire un salon", inline=False)
    embed.add_field(name="+ticket", value="Crée embed du ticket", inline=False)
    embed.add_field(name="+warn", value="Mettre un Warn", inline=False)
    embed.add_field(name="+ticket1", value="ajoute des ticket pour citoyen", inline=False)
    embed.add_field(name="+ticket2", value="ajoute des ticket pour les recrutement", inline=False)
    embed.add_field(name="+ticket3", value="ajoute des ticket pour les Stats", inline=False)
    embed.add_field(name="+remove", value="retirer une personne d'un ticket", inline=False)
    embed.add_field(name="+add", value="Ajouter une personne au ticket", inline=False)
    embed.add_field(name="+say", value="Envoyer un message avec le compte du bot", inline=False)
    embed.add_field(name="+massiverole", value="Ajouter un role a tout le serveur", inline=False)
    embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/1358734917365927966/2557ee3ba12480f959dd0ac59b691dd7.webp?size=1024&format=webp")
    await ctx.send(embed=embed)





@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Streaming(
        name=config["bot_status"], 
        url="https://www.twitch.tv/By%20LAS%20NOCHES%20ON%20TOP"  # Remplacez par l'URL du stream
    ))
    await bot.tree.sync()


Token = "MTM1ODczNDkxNzM2NTkyNzk2Ng.Guful0.zLJneRpoAnkTS0fPDKiQPpxDFhUT60fGrXKqWc"

# Lancer le bot
bot.run(Token)