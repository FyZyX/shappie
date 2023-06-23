import json
import os
import typing

import discord
import openai

from . import persona
from .. import datastore, llm, tool

MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PERSIST = bool(os.environ.get("PERSIST", False))

openai.api_key = OPENAI_API_KEY


def _get_relevant_tools(message: discord.Message):
    tools = tool.ToolCollection()
    relevant_keywords = filter(lambda k: k in message.content, tool.TOOLS)
    for keyword in relevant_keywords:
        tools.add_tool(keyword)

    return tools


async def select_tool(
        message: discord.Message,
        bot_persona: persona.Persona,
        tools: tool.ToolCollection,
) -> tuple[typing.Optional[typing.Callable], typing.Optional[dict]]:
    response = await llm.generate_response_message(
        message=message,
        persona=bot_persona,
        functions=tools.schema(),
    )
    print(response)
    function_call = response.get("function_call")
    if function_call:
        tool_name = function_call["name"]
        tool_args = json.loads(function_call["arguments"])

        return tools.get_tool(tool_name), tool_args

    return None, None


class Shappie(discord.Client):
    def __init__(self, *, intents: discord.Intents, **options: typing.Any):
        super().__init__(intents=intents, **options)
        self.tree = discord.app_commands.CommandTree(self)
        self._store = None
        if PERSIST:
            self._store = datastore.DataStore(MONGO_URI, MONGO_DB_NAME)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_message(self, message: discord.Message):
        if self._store:
            await self._store.save_message(message)

            if "http" in message.content:
                await self._store.save_link(message)

        if message.author.bot:
            return

        # if message.content == "!killit":
        #     await message.channel.purge()

        if self._store:
            bot_persona = await self._store.get_persona("default")
        else:
            bot_persona = persona.DEFAULT

        guild = message.guild
        shappie_member = guild.get_member(self.user.id)
        did_mention_role = set(shappie_member.roles).intersection(message.role_mentions)
        did_mention_bot = self.user in message.mentions or did_mention_role
        if did_mention_bot:
            async with message.channel.typing():
                response = await llm.generate_response_message(
                    message=message,
                    persona=bot_persona,
                )
            await message.reply(response["content"])

        tools = _get_relevant_tools(message)
        if len(tools):
            async with message.channel.typing():
                selected_tool, kwargs = await select_tool(message, bot_persona, tools)
                if selected_tool:
                    result = selected_tool(**kwargs)
                    await message.channel.send(result)
