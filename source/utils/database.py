import motor.motor_asyncio
from datetime import datetime
import pytz
from bson import ObjectId

from source.config import MONGO_URI


class DatabaseHandler:
    def __init__(self):
        """Initializes the database connection."""
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
        self.db = self.client.schedule_bot
        self.schedules = self.db.schedules
        print("DB Handler Initialized.")

    async def add_schedule(self, data: dict):
        """Adds a new schedule document to the collection."""
        return await self.schedules.insert_one(data)

    async def get_user_schedules(self, user_id: int):
        """Fetches all scheduled messages for a given user."""
        cursor = self.schedules.find({"user_id": user_id})
        return await cursor.to_list(length=100)

    async def get_due_schedules(self):
        """Fetches all schedules that are due to be sent."""
        now_utc = datetime.now(pytz.utc)
        cursor = self.schedules.find({"send_timestamp": {"$lte": now_utc}})
        return cursor

    async def count_schedules_in_guild(self, guild_id: int):
        """Counts the number of scheduled messages for a given guild."""
        return await self.schedules.count_documents({"guild_id": guild_id})

    async def delete_schedule_by_id(self, task_id: ObjectId):
        """Deletes a schedule by its MongoDB _id."""
        return await self.schedules.delete_one({"_id": task_id})

    async def update_schedule_by_id(self, task_id: ObjectId, updates: dict):
        """Updates a schedule by its MongoDB _id with new data."""
        return await self.schedules.update_one({"_id": task_id}, {"$set": updates})