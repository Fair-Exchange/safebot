import discord
import aiohttp
import requests
import datetime
import asyncio
import re
import bs4
import json

class Bot(discord.Client):
    prefix = "!"
    commands = {
        "block": "Current block height",
        "halve": "Days to block reward halving",
        "diff": "Current block difficulty",
        "nethash": "Current network hashrate",
        "blockreward": "Current block reward",
        "hashpower": "Calculate estimated earning with your hashrate",
        "poolhash": "Get Safecoin pools info",
    }
    pools = {
        "https://safe.coinblockers.com/": {
            "API": "https://safe.coinblockers.com/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "https://safecoin.equihub.pro/": {
            "API": "https://safecoin.equihub.pro/api/stats",
            "fn": lambda content: json.loads(content)["hashrate"],
        },
        "https://safecoin.voidr.net": {
            "API": "https://safecoin.voidr.net/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "https://safe.suprnova.cc/": {
            "API": "https://safe.suprnova.cc/index.php?page=statistics&action=pool",
            "fn": lambda content: float(bs4.BeautifulSoup(content, "html.parser").find_all("table", {"class":"table table-striped table-bordered table-hover"})[2].tbody.tr.td.span.text.replace(",", "")),
        },
        "https://minermore.com/pool/SAFE/": {
            "API": "https://minermore.com/api/status",
            "fn": lambda content: float(json.loads(content)["SAFE"]["hashrate"]),
        },
        "https://safe.solopool.org/": {
            "API": "https://safe.solopool.org/api/stats",
            "fn": lambda content: json.loads(content)["hashrate"],
        },
        "https://equipool.1ds.us": {
            "API": "https://equipool.1ds.us/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "http://safecoinpool.club/": {
            "API": "http://safecoinpool.club/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "https://safe.bitpool.ro/": {
            "API": "https://safe.bitpool.ro/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "https://safecoin.axepool.com/": {
            "API": "https://safecoin.axepool.com/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "http://www.macro-pool.com:8088/": {
            "API": "http://www.macro-pool.com:8088/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        },
        "http://zergpool.com": {
            "API": "http://api.zergpool.com:8080/api/currencies",
            "fn": lambda content: json.loads(content)["SAFE"]["hashrate"],
        }
        "https://equihash.pro": {
            "API": "https://equihash.pro/api/stats",
            "fn": lambda content: json.loads(content)["pools"]["safecoin"]["hashrate"]*2/10**6,
        }
    }
    pools_stat = {}
    blocks = 0
    difficulty = 0
    hashrate = 0
    last_pool_update = datetime.datetime.fromtimestamp(0)
    last_hashrate_update = datetime.datetime.fromtimestamp(0)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bg_task = self.loop.create_task(self.pool_update())
        self.bg2_task = self.loop.create_task(self.hashrate_update())

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel) or message.channel.name in ('pools', 'bot-commands'):
            if message.content and message.content.startswith(self.prefix):
                command = message.content.split()[0][1:].lower()
                if command == "help":
                    if not isinstance(message.channel, discord.DMChannel):
                        await message.channel.send(f"Hi {message.author.mention}. I have sent you a direct message with help info")
                    embed = discord.Embed(title="Bot commands for SafeBot", url="https://safecoin.org", color=0x131afe)
                    embed.set_author(name="SafeBot", url="http://www.safecoin.org",
                                    icon_url="https://safe.trade/assets/logo2-f90245b6bdcfa4f7582e36d0bc7c69d513934aa8c5a1c6cbc884ef91768bda00.png")
                    embed.add_field(name=f"{self.prefix}help", value="Get the commands of the bot", inline=False)
                    for command, value in self.commands.items():
                        embed.add_field(name=f"{self.prefix}{command}", value=value or "No docs", inline=False)
                    await message.author.send(f"Hi {message.author.mention}. Here are the commands for SafeBot", embed=embed)
                elif command in self.commands:
                    embed = discord.Embed()
                    embed.set_author(name="SafeBot", url="http://www.safecoin.org",
                                    icon_url="https://safe.trade/assets/logo2-f90245b6bdcfa4f7582e36d0bc7c69d513934aa8c5a1c6cbc884ef91768bda00.png")
                    fnout = getattr(self, command)(message.content[message.content.index(" "):] if " " in message.content else "", embed)
                    if isinstance(fnout, discord.Embed):
                        embed = fnout
                    else:
                        embed.add_field(name=command.capitalize(), value=f"{fnout}", inline=False)
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(f"Command not found. Write {self.prefix}help to get the command list")

    async def pool_update(self):
        await self.wait_until_ready()
        while not self.is_closed():
            async with aiohttp.ClientSession() as session:
                for pool, i in self.pools.items():
                    try:
                        async with session.get(i["API"], timeout=10) as response:
                            hashrate = float(i["fn"](await response.text()))
                    except:
                        self.pools_stat[pool] = None
                    else:
                        self.pools_stat[pool] = hashrate
                await session.close()
            self.last_pool_update = datetime.datetime.utcnow()
            await asyncio.sleep(60)

    async def hashrate_update(self):
        await self.wait_until_ready()
        while not self.is_closed():

            i = await getmininginfo()
            hashrate = i.get("networkhashps")
            if not hashrate is None:
                self.blocks = i.get("blocks")
                self.difficulty = i.get("difficulty")
                self.hashrate = hashrate
                self.last_hashrate_update = datetime.datetime.utcnow()
                await self.change_presence(status=discord.Status.online, activity=discord.Game(name=normalize_hashrate(hashrate)))
                await asyncio.sleep(45)
            else:
                await asyncio.sleep(1)

    def block(self, text, embed):
        embed.set_footer(text=f"Last update: {self.last_hashrate_update.ctime()}")
        return f"Current block is **{self.blocks}**"

    def halve(self, text, embed):
        schedule = [
            [64, 123840],
            [56, 178378],
            [48, 181378],
            [40, 184378],
            [32, 187378],
            [28, 197378],
            [24, 207378],
            [22, 217378],
            [20, 227378],
            [18, 237378],
            [16, 247378],
            [15, 287378],
            [14, 327378],
            [13, 367378],
            [12, 407378],
            [11, 447378],
            [10, 487378],
            [9, 527378],
            [8, 567378],
            [7, 647378],
            [6, 727378],
            [5, 807378],
            [4, 887378],
            [3, 1207378],
            [2, 1527378],
            [1, 1847378],
            [0.5, 2167378],
            [0.25, 3447378],
            [0.125, 5256000],
        ]
        embed.set_footer(text=f"Last update: {self.last_hashrate_update.ctime()}")
        for reward, blockHalving in schedule:
            if blockHalving > self.blocks:
                break
        else:
            return f"Current block: **{self.blocks}**\nThere are no more block reward halving!"
        return f"Current block: **{self.blocks}**\nNext block for halving: **{blockHalving}**\n**{(blockHalving-self.blocks)/24/60:.1f} days** left until block reward halving to **{reward} SAFEs**"

    def diff(self, text, embed):
        embed.set_footer(text=f"Last update: {self.last_hashrate_update.ctime()}")
        return f"Current difficulty is **{self.difficulty:0.2f}**"

    def nethash(self, text, embed):
        embed.set_footer(text=f"Last update: {self.last_hashrate_update.ctime()}")
        return f"Current network hash is **{normalize_hashrate(self.hashrate)}**"

    def blockreward(self, text, embed):
        return f"Current block reward is **{getblockreward():.0f} SAFE**"

    def hashpower(self, text, embed):
        if not text or text.isspace():
            return f"**Usage:** *{self.prefix}hashpower <hashrate>*"
        try:
            hashrate = float(text)
        except ValueError:
            return "Invalid hashrate"
        blockreward = getblockreward()
        embed.set_footer(text=f"Last update: {self.last_hashrate_update.ctime()}")
        return f"Network hash: {normalize_hashrate(self.hashrate)}\nWith **{normalize_hashrate(hashrate)}** you will get approximate {hashrate/self.hashrate*blockreward*60:.2f} SAFEs **per hour** and {hashrate/self.hashrate*blockreward*60*24:.2f} SAFEs **per day** at current network difficult."

    def poolhash(self, text, embed):
        poolsHashrate = sum(h for h in self.pools_stat.values() if h)
        embed.add_field(name="🇳 🇪 🇹 🇼 🇴 🇷 🇰", value=f"""Global Network Blocks: **{self.blocks}**
Global Network Diff: **{self.difficulty:.2f}**

Global Network Hash: **{normalize_hashrate(self.hashrate)}**
Global Pool Hash: **{normalize_hashrate(poolsHashrate)}**
Expected Global Hash: **{normalize_hashrate((self.hashrate+poolsHashrate)/2)}**""", inline=False)
        unknowhash = self.hashrate - poolsHashrate
        pools = ""
        for pool, pool_hashrate in sorted(self.pools_stat.items(), key=lambda kv: kv[1] or -1):
            if pool_hashrate is None:
                pools += f"❓<{pool}>: **unknown**\n"
            else:
                pHashrate = normalize_hashrate(pool_hashrate)
                hashPercentage = pool_hashrate*100/self.hashrate
                icon = pool_icon(hashPercentage)
                pools += f"{icon}<{pool}>: **{pHashrate}** (*{int(hashPercentage) if hashPercentage.is_integer() else round(hashPercentage, 2)}%*)\n"
        embed.add_field(name="🇵 🇴 🇴 🇱 🇸", value=f"""{pools}
❔Unknow pool/Solo hashrate: {f"{normalize_hashrate(unknowhash)} (*{unknowhash*100/self.hashrate:.2f}%*)" if unknowhash > 0 else '---'}""", inline=False)
        embed.set_footer(text=f"Last update: {self.last_pool_update.ctime()}")
        return embed

async def getmininginfo():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("http://127.0.0.1:8771/", auth=aiohttp.BasicAuth("user","password"), json={'method': 'getmininginfo'}) as response:
                return json.loads(await response.text()).get("result") or {}
        except:
            return {}

def getblockreward():
    try:
        return requests.post("http://127.0.0.1:8771/", auth=("user","password"), data='{"method": "getblocksubsidy"}').json()["result"]["miner"]
    except:
        return None

def normalize_hashrate(hashrate):
    if isinstance(hashrate, str):
        return hashrate
    if hashrate < 10**3:
        return f"{hashrate:.2f} Sol/s"
    return f"{hashrate/10**3:.2f} kSol/s"

def pool_icon(percentage):
    if percentage >= 50:
        return "🚫"
    if percentage >= 40:
        return "‼"
    if percentage >= 10:
        return "🎄"
    if percentage == 0:
        return "💤"
    return "🌱"

client = Bot()
client.run('TOKEN')