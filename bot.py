import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from pymongo import MongoClient

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# MongoDB接続
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["discord_bot"]
collection = db["verified_users"]

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="認証する", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        # 既に登録済みか確認してから追加
        if collection.find_one({"user_id": user_id}) is None:
            collection.insert_one({"user_id": user_id, "verified": True})
            await interaction.response.send_message("✅ 認証しました！", ephemeral=True)
        else:
            await interaction.response.send_message("✅ すでに認証済みです。", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot起動: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"スラッシュコマンド同期: {len(synced)}件")
    except Exception as e:
        print(e)

# 認証ボタンを送るコマンド
@bot.tree.command(name="send_verify", description="認証ボタンを送信します")
@app_commands.checks.has_permissions(administrator=True)
async def send_verify(interaction: discord.Interaction):
    await interaction.response.send_message(
        "サーバー参加者は下のボタンを押して認証してください。",
        view=VerifyButton()
    )

# 認証者全員にDM送信（削除不可・退会者も対象）
@bot.tree.command(name="dmall", description="認証済みユーザー全員にDMを送信します")
@app_commands.checks.has_permissions(administrator=True)
async def dmall(interaction: discord.Interaction, message: str):
    success = 0
    fail = 0
    await interaction.response.send_message("DM送信を開始します…", ephemeral=True)

    # MongoDBから認証済みユーザーを全取得
    verified_users = list(collection.find({"verified": True}))

    for data in verified_users:
        user_id = data["user_id"]
        user = await bot.fetch_user(user_id)
        try:
            await user.send(message)
            success += 1
        except:
            fail += 1

        await asyncio.sleep(2)  # レート制限回避のため2秒間隔

    await interaction.followup.send(f"✅ 送信完了！成功: {success}, 失敗: {fail}", ephemeral=True)

bot.run(os.getenv("BOT_TOKEN"))
