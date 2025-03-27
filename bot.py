import os
import json
import importlib.util
from pathlib import Path
import disnake
from disnake.ext import commands
import sys
import asyncio

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

MODULES_DIR = BASE_DIR / "modules"
SETTINGS_FILE = BASE_DIR / "settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        raise FileNotFoundError("Settings file settings.json not found!")
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)
    if "bot_token" not in settings or not settings["bot_token"]:
        raise ValueError("Bot token not specified or invalid in settings.json!")
    return settings

def load_modules():
    modules = {}
    on_off_file = MODULES_DIR / "on_off_modules.py"
    if not os.path.exists(on_off_file):
        return modules
    spec = importlib.util.spec_from_file_location("on_off_modules", on_off_file)
    on_off_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(on_off_module)
    enabled_modules = getattr(on_off_module, "enabled_modules", {})
    for module_file in MODULES_DIR.glob("*.py"):
        module_name = module_file.stem
        if module_name == "on_off_modules":
            continue
        if enabled_modules.get(module_name, False):
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules[module_name] = module
    return modules

settings = load_settings()
bot = commands.Bot(
    command_prefix=settings["bot_prefix"],
    intents=disnake.Intents.all(),
    help_command=None
)
modules = load_modules()

for module_name, module in modules.items():
    if hasattr(module, "setup"):
        module.setup(bot)

async def update_activity():
    settings = load_settings()
    activity_list = settings.get("activity_list", [])
    interval = settings.get("activity_interval", 30)
    if not activity_list or interval == 0:
        if activity_list:
            activity_type = {
                "playing": disnake.ActivityType.playing,
                "listening": disnake.ActivityType.listening,
                "watching": disnake.ActivityType.watching
            }.get(activity_list[0]["type"], disnake.ActivityType.playing)
            await bot.change_presence(activity=disnake.Activity(type=activity_type, name=activity_list[0]["text"]))
        return
    
    while True:
        for activity in activity_list:
            activity_type = {
                "playing": disnake.ActivityType.playing,
                "listening": disnake.ActivityType.listening,
                "watching": disnake.ActivityType.watching
            }.get(activity["type"], disnake.ActivityType.playing)
            await bot.change_presence(activity=disnake.Activity(type=activity_type, name=activity["text"]))
            await asyncio.sleep(interval)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} successfully started!")
    asyncio.create_task(update_activity())

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    content = message.content
    if not content.startswith(bot.command_prefix):
        return
    args = content[len(bot.command_prefix):].split()
    command = args[0].lower()
    args = args[1:]

    for module in modules.values():
        if hasattr(module, "execute_command"):
            result = await module.execute_command(command, message)
            if result is not None:
                if isinstance(result, disnake.Embed):
                    await message.channel.send(embed=result)
                else:
                    await message.channel.send(result)
                return
    embed = disnake.Embed(
        title="Command Not Found",
        description=f"The command `{command}` is not recognized.",
        color=disnake.Color.red()
    )
    await message.channel.send(embed=embed)

def start_bot():
    try:
        bot.run(settings["bot_token"])
    except Exception as e:
        print(f"Bot start error: {e}")

if __name__ == "__main__":
    start_bot()