import discord
import re
import os
from flask import Flask, jsonify
import asyncio
from threading import Thread
import time

app = Flask(__name__)
pet_servers = []

def parse_pet_embed(embed):
    name = None
    mutation = None
    dps = None
    tier = None
    jobId = None
    placeId = None
    players = None

    for field in embed.fields:
        if "Name" in field.name:
            name = field.value.strip()
        elif "Mutation" in field.name:
            mutation = field.value.strip()
        elif "Money" in field.name or "Per Sec" in field.name:
            dps = field.value.strip()
        elif "Tier" in field.name:
            tier = field.value.strip()
        elif "Players" in field.name:
            m = re.match(r"(\d+)/(\d+)", field.value.strip())
            if m:
                players = {
                    "current": int(m.group(1)),
                    "max": int(m.group(2))
                }
        elif "JOBID" in field.name:
            jobId = field.value.strip()
        elif "Join Script" in field.name:
            m = re.search(r'TeleportToPlaceInstance`\((\d+),\s*"([\w-]+)', field.value)
            if m:
                placeId = m.group(1)
                jobId2 = m.group(2)
            else:
                placeId = jobId2 = None

    if players and (3 <= players["current"] <= 7):
        if name and jobId and placeId:
            return {
                "name": name,
                "mutation": mutation or "",
                "dps": dps or "",
                "tier": tier or "",
                "players": f'{players["current"]}/{players["max"]}',
                "jobId": jobId,
                "placeId": placeId,
                "timestamp": discord.utils.utcnow().timestamp(),
            }
    return None

class PetClient(discord.Client):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

    async def on_message(self, message):
        if message.channel.id != int(os.getenv("CHANNEL_ID")):
            return

        for embed in message.embeds:
            pet = parse_pet_embed(embed)
            if pet:
                if not any(p["jobId"] == pet["jobId"] and p["name"] == pet["name"] for p in pet_servers):
                    pet_servers.append(pet)
                    print(f"Added pet: {pet['name']} {pet['jobId']} {pet['players']}")
                if len(pet_servers) > 20:
                    pet_servers.pop(0)
                break

@app.route('/recent-pets')
def recent_pets():
    now = time.time()
    filtered = [p for p in pet_servers if now - p["timestamp"] < 900]
    return jsonify(filtered)

# Vercel serverless function handler
def handler(event, context):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = PetClient(intents=discord.Intents.default())
    client.intents.message_content = True
    Thread(target=client.run, args=(os.getenv("DISCORD_TOKEN"),), daemon=True).start()
    return app(event, context)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
