# Vkingvx Discord Permission Bot

A small Discord bot that adds `/vkingvxsetup` and configures the Vkingvx streamer server.

## What it does
- Creates/updates the main roles
- Sets role permissions
- Creates the Vkingvx categories/channels if missing
- Makes the Staff category private
- Makes welcome/rules/announcements/live/schedule read-only
- Sets normal member chat/voice permissions
- Restricts the Muted role
- Safe to run more than once; it updates instead of intentionally duplicating matching channels/roles

## Setup on Windows

1. Install Python 3.11+ from python.org.
2. Open Command Prompt in this folder.
3. Run:
   pip install -r requirements.txt
4. Create a Discord application/bot in the Discord Developer Portal.
5. Enable the bot and invite it to your server with:
   - Manage Roles
   - Manage Channels
   - View Audit Log
   - Send Messages
   - Use Slash Commands
   - Administrator is simplest for the first setup, but only use it if you trust your own bot.
6. Set your bot token as an environment variable. Do NOT paste the token into this file or send it to anyone.
   PowerShell:
   $env:DISCORD_TOKEN="YOUR_BOT_TOKEN"
7. Run:
   python bot.py
8. In your Vkingvx server, type:
   /vkingvxsetup

IMPORTANT:
- Put the bot's role above the roles it needs to edit.
- Never share your bot token.
- The command itself requires the person running it to have Administrator.
