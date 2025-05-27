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
   
class PrivateManageView(discord.ui.View):
    
    class _AddMemberButton(discord.ui.Button):
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Создаем модальное окно для ввода ID пользователя
            class AddMemberModal(discord.ui.Modal):
                def __init__(self):
                    super().__init__(title="Добавление участника")
                    self.add_item(discord.ui.InputText(
                        label="ID или упоминание пользователя",
                        placeholder="Введите ID или упомяните пользователя",
                        required=True
                    ))
                
                async def callback(self, interaction: discord.Interaction):
                    await interaction.response.defer()
                    
                    # Получаем введенный текст
                    user_input = self.children[0].value
                    
                    # Извлекаем ID пользователя из упоминания или используем как есть
                    user_id = int(''.join(filter(str.isdigit, user_input)))
                    
                    session = get_async_session()
                    
                    # Проверяем существование пользователя
                    try:
                        user = await interaction.client.fetch_user(user_id)
                    except:
                        return await interaction.followup.send("Пользователь не найден!", ephemeral=True)
                    
                    # Проверяем, не является ли пользователь уже участником
                    room_member = (await session.execute(select(PrivateRoomMember).where(
                        PrivateRoomMember.room_id == self.view.room_id,
                        PrivateRoomMember.user_id == user_id
                    ))).scalar_one_or_none()
                    
                    if room_member:
                        return await interaction.followup.send("Этот пользователь уже является участником комнаты!", ephemeral=True)
                    
                    # Добавляем пользователя
                    log = PrivateRoomLog(
                        room_id=self.view.room_id,
                        action_type=PrivateActionTypeENUM.invite,
                        actor=interaction.user.id,
                        object=user_id
                    )
                    
                    session.add(log)
                    await session.commit()
                    
                    room_member = PrivateRoomMember(
                        user_id=user_id,
                        room_id=self.view.room_id,
                        log_id=log.id
                    )
                    
                    session.add(room_member)
                    await session.commit()
                    
                    # Отправляем приглашение пользователю
                    try:
                        await user.send(embeds=get_embeds("private/manage/menu/members/invitation", private_name=self.view.room_name))
                        await interaction.followup.send(f"Приглашение отправлено пользователю {user.mention}", ephemeral=True)
                    except:
                        await interaction.followup.send(f"Не удалось отправить приглашение пользователю {user.mention}. Возможно, у него закрыты личные сообщения.", ephemeral=True)
            
            await interaction.message.edit(view=None)
            await interaction.response.send_modal(AddMemberModal())
            
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.green,
                           label="Добавить участника",
                           row=0)
    
    class _RemoveMemberSelect(discord.ui.Select):
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Получаем ID выбранного пользователя
            user_id = int(self.values[0])
            
            session = get_async_session()
            
            # Удаляем пользователя из комнаты
            room_member = (await session.execute(select(PrivateRoomMember).where(
                PrivateRoomMember.room_id == self.view.room_id,
                PrivateRoomMember.user_id == user_id
            ))).scalar_one_or_none()
            
            if room_member:
                # Создаем лог удаления
                log = PrivateRoomLog(
                    room_id=self.view.room_id,
                    action_type=PrivateActionTypeENUM.kick,
                    actor=interaction.user.id,
                    object=user_id
                )
                
                session.add(log)
                await session.commit()
                
                # Удаляем участника
                await session.delete(room_member)
                await session.commit()
                
                await interaction.followup.send(f"Участник успешно удален из комнаты!", ephemeral=True)
            else:
                await interaction.followup.send("Участник не найден!", ephemeral=True)
            
            # Обновляем список участников
            members = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.room_id == self.view.room_id))).scalars().all()
            
            options = []
            for member in members:
                user = await interaction.client.fetch_user(member.user_id)
                options.append(discord.SelectOption(
                    label=user.name,
                    value=str(user.id),
                    description=f"ID: {user.id}"
                ))
            
            self.options = options
            await interaction.message.edit(view=self.view)
    
    class _RemoveMemberButton(discord.ui.Button):
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            
            session = get_async_session()
            
            # Получаем список участников
            members = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.room_id == self.view.room_id))).scalars().all()
            
            options = []
            for member in members:
                user = await interaction.client.fetch_user(member.user_id)
                options.append(discord.SelectOption(
                    label=user.name,
                    value=str(user.id),
                    description=f"ID: {user.id}"
                ))
            
            # Создаем Select с участниками
            select = self.view._RemoveMemberSelect(
                placeholder="Выберите участника для удаления",
                options=options,
                row=0
            )
            
            # Создаем новое view с Select
            view = discord.ui.View(timeout=None)
            view.add_item(select)
            
            await interaction.message.edit(view=view)
            
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.red,
                           label="Удалить участника",
                           row=0)
    
    class _SettingsButton(discord.ui.Button):
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            
            # Создаем view с кнопками настроек
            class SettingsView(discord.ui.View):
                class _ChangeNameButton(discord.ui.Button):
                    async def callback(self, interaction: discord.Interaction):
                        
                        class ChangeNameModal(discord.ui.Modal):
                            def __init__(self):
                                super().__init__(title="Изменение названия")
                                self.add_item(discord.ui.InputText(
                                    label="Новое название",
                                    placeholder="Введите новое название комнаты",
                                    required=True
                                ))
                            
                            async def callback(self, interaction: discord.Interaction):
                                await interaction.response.defer()
                                
                                session = get_async_session()
                                
                                # Обновляем название комнаты
                                private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.id == self.view.room_id))).scalar_one_or_none()
                                
                                if private_room:
                                    # Создаем лог изменения
                                    log = PrivateRoomLog(
                                        room_id=self.view.room_id,
                                        action_type=PrivateActionTypeENUM.change,
                                        actor=interaction.user.id,
                                        before=private_room.label,
                                        after=self.children[0].value
                                    )
                                    
                                    session.add(log)
                                    await session.commit()
                                    
                                    # Обновляем название
                                    private_room.label = self.children[0].value
                                    await session.commit()
                                    
                                    await interaction.followup.send("Название комнаты успешно изменено!", ephemeral=True)
                                else:
                                    await interaction.followup.send("Комната не найдена!", ephemeral=True)
                        
                        try:
                            await interaction.message.edit(view=None)
                            await interaction.response.send_modal(ChangeNameModal())
                        except discord.NotFound:
                            await interaction.followup.send("Сообщение больше не доступно. Пожалуйста, используйте команду снова.", ephemeral=True)
                    
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.gray,
                                       label="Сменить название",
                                       row=0)
                
                class _ChangeColorButton(discord.ui.Button):
                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.defer()
                        
                        class ChangeColorModal(discord.ui.Modal):
                            def __init__(self):
                                super().__init__(title="Изменение цвета")
                                self.add_item(discord.ui.InputText(
                                    label="Новый цвет",
                                    placeholder="Введите цвет в HEX формате (например, #FF0000)",
                                    required=True
                                ))
                            
                            async def callback(self, interaction: discord.Interaction):
                                await interaction.response.defer()
                                
                                # Валидация HEX-цвета
                                color_hex = self.children[0].value.strip('#')
                                try:
                                    color = int(color_hex, 16)
                                except ValueError:
                                    return await interaction.followup.send("Неверный формат цвета! Используйте HEX-формат (например, #FF0000)", ephemeral=True)
                                
                                session = get_async_session()
                                
                                # Обновляем цвет комнаты
                                private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.id == self.view.room_id))).scalar_one_or_none()
                                
                                if private_room:
                                    # Создаем лог изменения
                                    log = PrivateRoomLog(
                                        room_id=self.view.room_id,
                                        action_type=PrivateActionTypeENUM.change,
                                        actor=interaction.user.id,
                                        before=private_room.color,
                                        after=str(color)
                                    )
                                    
                                    session.add(log)
                                    await session.commit()
                                    
                                    # Обновляем цвет
                                    private_room.color = str(color)
                                    await session.commit()
                                    
                                    # Обновляем цвет роли
                                    guild = await interaction.client.fetch_guild(1307622842048839731)
                                    role = await guild._fetch_role(self.view.room_id)
                                    await role.edit(color=discord.Color(color))
                                    
                                    await interaction.followup.send("Цвет комнаты успешно изменен!", ephemeral=True)
                                else:
                                    await interaction.followup.send("Комната не найдена!", ephemeral=True)
                        
                        try:
                            await interaction.message.edit(view=None)
                            await interaction.response.send_modal(ChangeColorModal())
                        except discord.NotFound:
                            await interaction.followup.send("Сообщение больше не доступно. Пожалуйста, используйте команду снова.", ephemeral=True)
                    
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.gray,
                                       label="Сменить цвет",
                                       row=0)
                
                class _ChangeIconButton(discord.ui.Button):
                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.defer()
                        
                        class ChangeIconModal(discord.ui.Modal):
                            def __init__(self):
                                super().__init__(title="Изменение иконки")
                                self.add_item(discord.ui.InputText(
                                    label="Ссылка на иконку",
                                    placeholder="Введите ссылку на новую иконку",
                                    required=True
                                ))
                            
                            async def callback(self, interaction: discord.Interaction):
                                await interaction.response.defer()
                                
                                session = get_async_session()
                                
                                # Обновляем иконку комнаты
                                private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.id == self.view.room_id))).scalar_one_or_none()
                                
                                if private_room:
                                    # Создаем лог изменения
                                    log = PrivateRoomLog(
                                        room_id=self.view.room_id,
                                        action_type=PrivateActionTypeENUM.change,
                                        actor=interaction.user.id,
                                        before=private_room.icon,
                                        after=self.children[0].value
                                    )
                                    
                                    session.add(log)
                                    await session.commit()
                                    
                                    # Обновляем иконку
                                    private_room.icon = self.children[0].value
                                    await session.commit()
                                    
                                    # Обновляем иконку роли
                                    guild = await interaction.client.fetch_guild(1307622842048839731)
                                    role = await guild._fetch_role(self.view.room_id)
                                    await role.edit(display_icon=self.children[0].value)
                                    
                                    await interaction.followup.send("Иконка комнаты успешно изменена!", ephemeral=True)
                                else:
                                    await interaction.followup.send("Комната не найдена!", ephemeral=True)
                        
                        try:
                            await interaction.message.edit(view=None)
                            await interaction.response.send_modal(ChangeIconModal())
                        except discord.NotFound:
                            await interaction.followup.send("Сообщение больше не доступно. Пожалуйста, используйте команду снова.", ephemeral=True)
                    
                    def __init__(self):
                        super().__init__(style=discord.ButtonStyle.gray,
                                       label="Сменить иконку",
                                       row=0)
                
                def __init__(self, room_id: int):
                    super().__init__(timeout=None)
                    self.room_id = room_id
                    
                    self.add_item(self._ChangeNameButton())
                    self.add_item(self._ChangeColorButton())
                    self.add_item(self._ChangeIconButton())
            
            try:
                view = SettingsView(room_id=self.view.room_id)
                # Отправляем новое сообщение с настройками вместо редактирования
                await interaction.followup.send("Настройки приватной комнаты:", view=view)
            except discord.NotFound:
                await interaction.followup.send("Сообщение больше не доступно. Пожалуйста, используйте команду снова.", ephemeral=True)
            
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.gray,
                           label="Настройки",
                           row=0)
    
    class _ExitButton(discord.ui.Button):
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            
            session = get_async_session()
            
            # Удаляем пользователя из комнаты
            room_member = (await session.execute(select(PrivateRoomMember).where(
                PrivateRoomMember.room_id == self.view.room_id,
                PrivateRoomMember.user_id == interaction.user.id
            ))).scalar_one_or_none()
            
            if room_member:
                # Создаем лог выхода
                log = PrivateRoomLog(
                    room_id=self.view.room_id,
                    action_type=PrivateActionTypeENUM.kick,
                    actor=interaction.user.id,
                    object=interaction.user.id
                )
                
                session.add(log)
                await session.commit()
                
                # Удаляем участника
                await session.delete(room_member)
                await session.commit()
                
                await interaction.message.edit(view=None)
                await interaction.followup.send("Вы успешно покинули комнату!", ephemeral=True)
            else:
                await interaction.followup.send("Вы не являетесь участником этой комнаты!", ephemeral=True)
            
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.red,
                           label="Покинуть комнату",
                           row=1)
    
    class _DeleteButton(discord.ui.Button):
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            
            session = get_async_session()
            
            # Удаляем комнату
            private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.id == self.view.room_id))).scalar_one_or_none()
            
            if private_room:
                # Создаем лог удаления
                log = PrivateRoomLog(
                    room_id=self.view.room_id,
                    action_type=PrivateActionTypeENUM.change,
                    actor=interaction.user.id,
                    before="exists",
                    after="deleted"
                )
                
                session.add(log)
                await session.commit()
                
                # Удаляем комнату
                await session.delete(private_room)
                await session.commit()
                
                await interaction.message.edit(view=None)
                await interaction.followup.send("Комната успешно удалена!", ephemeral=True)
            else:
                await interaction.followup.send("Комната не найдена!", ephemeral=True)
            
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.danger,
                           label="Удалить комнату",
                           row=1)
    
    def __init__(self, room_name: str, room_id: int, members_list: str, is_owner: bool):
        super().__init__(timeout=None)
        self.room_name = room_name
        self.room_id = room_id
        self.members_list = members_list
        
        # Добавляем кнопки управления
        if is_owner:
            self.add_item(self._AddMemberButton())
            self.add_item(self._RemoveMemberButton())
            self.add_item(self._SettingsButton())
        
        # Если пользователь не владелец, показываем кнопку выхода
        if not is_owner:
            self.add_item(self._ExitButton())
        # Если владелец, показываем кнопку удаления
        else:
            self.add_item(self._DeleteButton())

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

    @private_manage_subgroup.command(name="menu")
    async def private_manage_menu_command(self, 
                                        ctx: discord.ApplicationContext,
                                        room_id: int = None):
        
        await ctx.defer(ephemeral=True)
        
        session = get_async_session()
        
        if not room_id:
            # Проверяем, есть ли у пользователя своя приватка
            private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == ctx.interaction.user.id))).scalar_one_or_none()
            
            if not private_room:
                return await ctx.followup.send(embeds=get_embeds("private/manage/no_rooms"), ephemeral=True)
            
            room_id = private_room.id
        
        # Проверяем существование приватки
        private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.id == room_id))).scalar_one_or_none()
        
        if not private_room:
            return await ctx.followup.send(embeds=get_embeds("private/manage/no_exists", room_id=room_id), ephemeral=True)
        
        # Проверяем доступ
        is_owner = private_room.owner_id == ctx.interaction.user.id
        is_member = (await session.execute(select(PrivateRoomMember).where(
            PrivateRoomMember.room_id == room_id,
            PrivateRoomMember.user_id == ctx.interaction.user.id
        ))).scalar_one_or_none()
        
        if not (is_owner or is_member):
            return await ctx.followup.send(embeds=get_embeds("private/manage/forbidden", room_id=room_id), ephemeral=True)
        
        # Получаем количество участников
        members = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.room_id == room_id))).scalars().all()
        
        # Формируем список участников
        members_list = ""
        for member in members:
            user = await ctx.bot.fetch_user(member.user_id)
            members_list += f"• {user.mention}\n"
        
        # Создаем view с кнопками
        view = PrivateManageView(
            room_name=private_room.label,
            room_id=room_id,
            members_list=members_list,
            is_owner=is_owner
        )
        
        # Получаем цвет для эмбеда
        try:
            color = int(private_room.color) if private_room.color else 3092790
        except (ValueError, TypeError):
            color = 3092790
        
        # Отправляем меню управления
        await ctx.followup.send(embeds=get_embeds("private/manage/menu/main",
                                                room_name=private_room.label,
                                                owner_id=private_room.owner_id,
                                                members_count=len(members),
                                                room_id=room_id,
                                                color=color),
                              view=view,
                              ephemeral=True)

    @private_manage_subgroup.command(name="revoke")
    async def private_manage_revoke_command(self,
                                          ctx: discord.ApplicationContext,
                                          member: discord.Member):
        
        await ctx.defer(ephemeral=True)
        
        session = get_async_session()
        
        # Проверяем, есть ли у пользователя своя приватка
        private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == ctx.interaction.user.id))).scalar_one_or_none()
        
        if not private_room:
            return await ctx.followup.send(embeds=get_embeds("private/manage/no_rooms"), ephemeral=True)
        
        # Проверяем, является ли указанный пользователь участником
        room_member = (await session.execute(select(PrivateRoomMember).where(
            PrivateRoomMember.room_id == private_room.id,
            PrivateRoomMember.user_id == member.id
        ))).scalar_one_or_none()
        
        if not room_member:
            return await ctx.followup.send("Этот пользователь не является участником вашей приватной комнаты!", ephemeral=True)
        
        # Получаем список всех участников
        members = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.room_id == private_room.id))).scalars().all()
        
        members_list = ""
        for m in members:
            user = await ctx.bot.fetch_user(m.user_id)
            members_list += f"• {user.mention}\n"
        
        await ctx.followup.send(embeds=get_embeds("private/manage/menu/members/revoke", members_list=members_list), ephemeral=True)

    @private_manage_subgroup.command(name="exit")
    async def private_manage_exit_command(self,
                                        ctx: discord.ApplicationContext):
        
        await ctx.defer(ephemeral=True)
        
        session = get_async_session()
        
        # Проверяем, является ли пользователь участником какой-либо приватки
        room_member = (await session.execute(select(PrivateRoomMember).where(PrivateRoomMember.user_id == ctx.interaction.user.id))).scalar_one_or_none()
        
        if not room_member:
            return await ctx.followup.send("Вы не являетесь участником какой-либо приватной комнаты!", ephemeral=True)
        
        # Получаем информацию о приватке
        private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.id == room_member.room_id))).scalar_one_or_none()
        
        if private_room.owner_id == ctx.interaction.user.id:
            return await ctx.followup.send("Владелец не может покинуть свою приватную комнату! Используйте команду удаления комнаты.", ephemeral=True)
        
        await ctx.followup.send(embeds=get_embeds("private/manage/menu/exit", room_name=private_room.label), ephemeral=True)

    @private_manage_subgroup.command(name="delete")
    async def private_manage_delete_command(self,
                                          ctx: discord.ApplicationContext):
        
        await ctx.defer(ephemeral=True)
        
        session = get_async_session()
        
        # Проверяем, есть ли у пользователя своя приватка
        private_room = (await session.execute(select(PrivateRoom).where(PrivateRoom.owner_id == ctx.interaction.user.id))).scalar_one_or_none()
        
        if not private_room:
            return await ctx.followup.send(embeds=get_embeds("private/manage/no_rooms"), ephemeral=True)
        
        await ctx.followup.send(embeds=get_embeds("private/manage/menu/delete", room_name=private_room.label), ephemeral=True)