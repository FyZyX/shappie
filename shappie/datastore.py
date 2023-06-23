import discord
import motor.motor_asyncio

from . import bot


class DataStore:
    def __init__(self, url, db_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(url)
        self._db: motor.motor_asyncio.AsyncIOMotorDatabase = self._client[db_name]
        self._messages = self._get_collection("messages")
        self._links = self._get_collection("links")
        self._personas = self._get_collection("personas")

    def _get_collection(self, collection_name: str):
        return self._db[collection_name]

    async def save_message(self, message: discord.Message):
        if not message.guild:
            await self._messages.insert_one({
                "server": message.guild.name,
                "channel": message.channel.name,
                "sender": message.author.name,
                "message": message.content,
                "time": message.created_at,
            })
        else:
            await self._messages.insert_one({
                "channel": message.channel.name,
                "sender": message.author.name,
                "message": message.content,
                "time": message.created_at,
            })

    async def save_link(self, message: discord.Message):
        await self._links.insert_one({
            "server": message.guild.name,
            "channel": message.channel.name,
            "sender": message.author.name,
            "link": message.content,
            "time": message.created_at,
        })

    async def add_persona(self, persona: bot.persona.Persona):
        await self._personas.insert_one(persona.json())

    async def update_persona(self, name, new_description):
        await self._personas.update_one(
            {"name": name},
            {"$set": {"description": new_description}}
        )

    async def delete_persona(self, name):
        await self._personas.delete_one({"name": name})

    async def get_persona(self, name):
        doc = await self._personas.find_one({"name": name})
        if doc:
            return bot.persona.Persona(doc["name"], doc["description"])
        else:
            return None
