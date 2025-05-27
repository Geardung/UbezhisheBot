from datetime import datetime
import discord
from discord.ext import commands, tasks
from typing import Union
from database import get_async_session
from models import PrivateActionTypeENUM, PrivateRoom, PrivateRoomLog, PrivateRoomMember, TimeCounterLog, TimeParse, User, VoiceLogTypeENUM
from utils import get_embeds
from sqlalchemy import select

PRIVATE_CATEGORY = 1331257581255131167 # Категория где все войсы
CREATE_PRIVATE_ROOM = 1331265751788818433 # Войс для создания приватки

class RoomInviteView(discord.ui.View):
    
    class _AcceptButton(discord.ui.Button):
        
        async def callback(self, interaction: discord.Interaction):
            
            await interaction.response.defer()
            
            session = get_async_session()
            
            guild = await interaction.client.fetch_guild(1307622842048839731)
            
            member = await guild.fetch_member(interaction.user.id)
            
            role = await guild._fetch_role(self.view.role_id)
            
            await member.add_roles(role)
            
            log = PrivateRoomLog(room_id=self.view.role_id,
                           action_type=PrivateActionTypeENUM.invite,
                           object=member.id)
            
            session.add(log)
            await session.commit()
            
            room_member = PrivateRoomMember(user_id=interaction.user.id,
                              room_id=self.view.role_id,
                              log_id=log.id)
            
            session.add(room_member)
            await session.commit()
            
            await interaction.message.edit(view=None, embeds=get_embeds("private\manage\menu\members\invitation_accepted"))

        def __init__(self):
            
            super().__init__(style=discord.ButtonStyle.green, 
                             label='Принять приглашение', 
                             disabled=False, 
                             row=1)
    
    def __init__(self, role_id: int, timeout = None, disable_on_timeout: bool = False, ):
        
        self.role_id = role_id
        
        super().__init__(
                         self._AcceptButton(),
                         timeout=timeout, 
                         disable_on_timeout=disable_on_timeout)

class CreateRoomView(discord.ui.View):
    
    def __init__(self, timeout = None, disable_on_timeout: bool = False):
        
        super().__init__(self._AgreeButton(),
                         self._DisagreeButton(),
                         timeout=timeout, 
                         disable_on_timeout=disable_on_timeout)
        
    class _AgreeButton(discord.ui.Button):
        
        async def callback(self, interaction: discord.Interaction):
            
            await interaction.response.defer()
            
            await interaction.message.edit(view=CreateProcessView(), embeds=get_embeds("private/create/process"))
            
            
        def __init__(self):
            
            super().__init__(style=discord.ButtonStyle.green, 
                             label='Я согласен!', 
                             disabled=False, 
                             row=1)
            
    class _DisagreeButton(discord.ui.Button):
        
        async def callback(self, interaction: discord.Interaction): 
            await interaction.response.defer()
            await interaction.message.delete()
            
        def __init__(self):
            
            super().__init__(style=discord.ButtonStyle.red, 
                             label='Отмена!', 
                             disabled=False, 
                             row=1)

class CreateProcessView(discord.ui.View):
    
    class _CreationProcessModal(discord.ui.Modal):
        
        async def callback(self, interaction: discord.Interaction):
            
            await interaction.response.defer()
            
            # Валидация HEX-цвета
            color_hex = self.children[2].value.strip('#')
            try:
                color = int(color_hex, 16)
            except ValueError:
                return await interaction.followup.send("Неверный формат цвета! Используйте HEX-формат (например, #FF0000)", ephemeral=True)
            
            guild = await interaction.client.fetch_guild(1307622842048839731)
            
            # Создаем роль с цветом и иконкой
            role = await guild.create_role(
                name=self.children[0].value,
                color=discord.Color(color),
                display_icon=self.children[1].value if self.children[1].value else None
            )
            
            member = await guild.fetch_member(interaction.user.id)
            
            await member.add_roles(role)
            
            room = PrivateRoom(
                id=role.id,
                owner_id=interaction.user.id,
                label=self.children[0].value,
                color=str(color),
                icon=self.children[1].value if self.children[1].value else ""
            )
            
            session = get_async_session()
            
            session.add(room)
            await session.commit()
            await session.close()
            
            return await interaction.message.edit(view=CreateSuccessView(), embeds=get_embeds("private/create/success"))
    
        def __init__(self, custom_id = None, timeout = None) -> None:
            super().__init__(*[discord.ui.InputText(style=discord.InputTextStyle.short, 
                                                    label='Название приватки'),
                               discord.ui.InputText(style=discord.InputTextStyle.singleline, 
                                                    label='Ссылка на картинку (необязательно)',
                                                    required=False,
                                                    placeholder='https://example.com/image.png'),
                               discord.ui.InputText(style=discord.InputTextStyle.short, 
                                                    label='Цвет в HEX формате',
                                                    placeholder='#FF0000')
                               ], 
                             title='Создание приватки')
    
    class _StartCreationButton(discord.ui.Button):
        
        async def callback(self, interaction: discord.Interaction):
            
            await interaction.response.send_modal(self.view._CreationProcessModal())
            
        def __init__(self):
            
            super().__init__(style=discord.ButtonStyle.gray, 
                             label='Готов заполнить анкету!', 
                             disabled=False, 
                             row=1)
    
    def __init__(self, timeout = None, disable_on_timeout: bool = False):
        super().__init__(
                         self._StartCreationButton(),
                         timeout=timeout, 
                         disable_on_timeout=disable_on_timeout)

class CreateSuccessView(discord.ui.View):
    
    async def on_timeout(self):
    
        return await self.message.delete()
    
    def __init__(self, timeout = 15, disable_on_timeout: bool = False):
        super().__init__(timeout=timeout, 
                         disable_on_timeout=disable_on_timeout)
   
class RoomsCog(discord.Cog):
    
    def __init__(self, bot: discord.Bot):
        
        self.bot: discord.Bot = bot
        
        super().__init__()
    
    private_group = discord.SlashCommandGroup("private")
    private_manage_subgroup = private_group.create_subgroup("manage")
    private_admin_subgroup = private_group.create_subgroup("admin", default_member_permissions=discord.Permissions(8))
    
    @private_group.command(name="create")
    async def private_create_command(self, 
                                     ctx: discord.ApplicationContext):
        
        await ctx.defer(ephemeral=True)
        
        session = get_async_session()
            
        private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == ctx.interaction.user.id))).scalar_one_or_none()
        
        if not private_room: 
            await ctx.interaction.user.send(embeds=get_embeds("private/create/first"),
                                                                    view=CreateRoomView())
            return await ctx.followup.send("Отправил в личные сообщения", ephemeral=True)
        else: return await ctx.followup.send(embeds=get_embeds("private/create/hasprivate",
                                                               role_id=private_room.role_id), ephemeral=True)
    
    
    
    @private_manage_subgroup.command(name="invite")
    async def private_manage_command(self, 
                                     ctx: discord.ApplicationContext,
                                     member: discord.Member):
        
        await ctx.defer(ephemeral=True)
        
        session = get_async_session()
            
        private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == ctx.interaction.user.id))).scalar_one_or_none()
        
        if not private_room: 
            await ctx.interaction.user.send(embeds=get_embeds("private/create/first"),
                                                                    view=CreateRoomView())
            return await ctx.followup.send(f"У тебя нет приватной комнаты!\nОтправил инструкцию по её создании в личные сообщения с ботом. Перейди прямо сюда -> <@{ctx.bot.user.id}>", ephemeral=True)
        else: 
            
            await member.send(view=RoomInviteView(private_room.id), embeds=get_embeds("private/manage/menu/members/invitation",
                                                                                      private_name=private_room.label))
            
            await ctx.followup.send(embeds=get_embeds("private/manage/menu/members/invited", user_id=member.id))
            
    
    @private_admin_subgroup.command(name="delete")
    async def private_admin_delete_command(self, 
                                       ctx: discord.ApplicationContext,
                                       private_role: discord.Role,
                                       safe_role: bool = False):
        
        session = get_async_session()
        
        await ctx.defer()
        
        #TODO проверить роль на причастие к приватке и уже тогда удалять приватку с ролькой.\
        #TODO Сохранять роль если будет параметр safe_role=True
    
    @private_admin_subgroup.command(name="create")
    async def private_admin_create_command(self, 
                                       ctx: discord.ApplicationContext,
                                       private_role: discord.Role):
    
        session = get_async_session()
        
        await ctx.defer()
    
    @commands.Cog.listener()
    async def on_ready(self):
        
        category: discord.CategoryChannel = await self.bot.fetch_channel(PRIVATE_CATEGORY)
        
        for chnl in category.voice_channels:
            
            if chnl.id == CREATE_PRIVATE_ROOM: continue
            
            if not chnl.members: await chnl.delete()
        
    @commands.Cog.listener(name="on_voice_state_update")
    async def on_exit_private(self, 
                              member: discord.Member,
                              before: discord.VoiceState,
                              after: discord.VoiceState):
        
        if member.bot: return # Игнорирование ботов.
        
        if before.channel: # Если вышел из приватки
            print(before.channel.members)
            try:
                if (before.channel.id != CREATE_PRIVATE_ROOM) and \
                (len(before.channel.members) == 0) and (before.channel.category_id == PRIVATE_CATEGORY):
                    
                    await before.channel.delete()
            
            except: pass
                
    @commands.Cog.listener(name="on_voice_state_update")
    async def on_join_in_create_private(self, 
                                    member: discord.Member,
                                    before: discord.VoiceState,
                                    after: discord.VoiceState):
        
        if member.bot: return # Игнорирование ботов.
        
        if after: # Если чел зашёл в войс для создания приватки
            
            if after.channel: 
            
                if (after.channel.id == CREATE_PRIVATE_ROOM):
                    
                    session = get_async_session()
                    
                    private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == member.id))).scalar_one_or_none()
                    
                    if not private_room: 
                        await member.move_to(None)
                        return await member.send(embeds=get_embeds("private/create/first"),
                                                                view=CreateRoomView())
                    
                    category:discord.CategoryChannel = await self.bot.fetch_channel(PRIVATE_CATEGORY)
                    
                    overwr_dict = {member: discord.PermissionOverwrite(connect=True,
                                                                    #mute_members=True, # Под вопросом
                                                                    #deafen_members=True, # Под вопросом
                                                                    move_members=True,
                                                                    speak=True, 
                                                                    send_messages=True, 
                                                                    stream=True,
                                                                    read_messages=True, 
                                                                    view_channel=True),
                                   category.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False, send_messages=False)
                                   }
                    
                    room_members = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.room_id == private_room.id))).scalars().all()

                    for room_mmbr in room_members:
                        
                        _ = await self.bot.fetch_user(room_mmbr.user_id)
                        
                        overwr_dict.update({_: discord.PermissionOverwrite(connect=True, 
                                                                        speak=True, 
                                                                        send_messages=True,
                                                                        stream=True,
                                                                        read_messages=True, 
                                                                        view_channel=True)})
                    
                    new_channel = await category.create_voice_channel(name=private_room.label,
                                                                    overwrites=overwr_dict)
                    
                    await member.move_to(new_channel)

    async def check_room_permissions(self, user_id: int, room_id: int) -> bool:
        session = get_async_session()
        room = await session.execute(select(PrivateRoom).where(PrivateRoom.id == room_id))
        return room.owner_id == user_id

    @private_admin_delete_command.error
    async def private_admin_delete_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, discord.NotFound):
            await ctx.followup.send("Комната не найдена", ephemeral=True)
        elif isinstance(error, discord.Forbidden):
            await ctx.followup.send("Недостаточно прав", ephemeral=True)
        else:
            await ctx.followup.send(f"Произошла ошибка: {str(error)}", ephemeral=True)