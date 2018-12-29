import discord
import requests
import datetime
import asyncio
import re
import bs4
import json
import datetime

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
        "http://safe.pool.sexy/": lambda: requests.get("http://safe.pool.sexy/api6/stats").json()["hashrate"],
        "https://cryptocommunity.network/": lambda: requests.get("https://cryptocommunity.network/api/stats").json()["pools"]["safecoin"]["hashrate"]*2/10**6,
        "https://equigems.online/": lambda: requests.get("https://equigems.online/api/stats").json()["pools"]["safecoin"]["hashrate"]*2/10**6,
        "https://safe.coinblockers.com/": lambda: requests.get("https://safe.coinblockers.com/api/stats").json()["pools"]["safecoin"]["hashrate"]*2/10**6,
        "https://safecoin.equihub.pro/": lambda: requests.get("https://safecoin.equihub.pro/api/stats").json()["hashrate"],
        "https://coorp.io/pool/safe": lambda: json.loads(re.search(r"\[[^\]]+\]", bs4.BeautifulSoup(requests.get("https://coorp.io/pool/safe").content, "html.parser").find(lambda tag: tag.name == "script" and "var coins_stat" in tag.text).text).group())[-1]["hashrate"]*2/10**6,
        "https://safecoin.voidr.net": lambda: requests.get("https://safecoin.voidr.net/api/stats").json()["pools"]["safecoin"]["hashrate"]*2/10**6,
        "https://safe.suprnova.cc/": lambda: float(bs4.BeautifulSoup(requests.get("https://safe.suprnova.cc/index.php?page=statistics&action=pool").content, "html.parser").find_all("table", {"class":"table table-striped table-bordered table-hover"})[2].tbody.tr.td.span.text.replace(",", "")),
        "https://minermore.com/pool/SAFE/": lambda: float(requests.get("https://minermore.com/api/status").json()["SAFE"]["hashrate"]),
        "https://safe.solopool.org/": lambda: requests.get("https://safe.solopool.org/api/stats").json()["hashrate"],
        "https://equipool.1ds.us": lambda: requests.get("https://equipool.1ds.us/api/stats").json()["pools"]["safecoin"]["hashrate"]*2/10**6,
        "http://safecoinpool.club/": lambda: requests.get("http://safecoinpool.club/api/stats").json()["pools"]["safecoin"]["hashrate"]*2/10**6,
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
            for pool, fn in self.pools.items():
                try:
                    hashrate = float(fn())
                except:
                    self.pools_stat[pool] = None
                else:
                    self.pools_stat[pool] = hashrate
            self.last_pool_update = datetime.datetime.utcnow()
            await asyncio.sleep(45)

    async def hashrate_update(self):
        await self.wait_until_ready()
        while not self.is_closed():
            i = getmininginfo()
            print(i)
            hashrate = i.get("networkhashps")
            if not hashrate is None:
                print("Done")
                self.blocks = i.get("blocks")
                self.difficulty = i.get("difficulty")
                self.hashrate = hashrate
                self.last_hashrate_update = datetime.datetime.utcnow()
                await self.change_presence(status=discord.Status.online, activity=discord.Game(name=normalize_hashrate(hashrate)))
            await asyncio.sleep(45)

    def block(self, text, embed):
        embed.set_footer(text=f"Last update: {self.last_hashrate_update.ctime()}")
        return f"Current block is **{self.blocks}**"

    def halve(self, text, embed):
        schedule = [
            [64, 175375],
            [55, 178375],
            [48, 181375],
            [40, 184375],
            [32, 187375],
            [28, 197375],
            [24, 207375],
            [22, 217375],
            [20, 227375],
            [18, 237375],
            [16, 247375],
            [15, 287375],
            [14, 327375],
            [13, 367375],
            [12, 407375],
            [11, 447375],
            [10, 487375],
            [9, 527375],
            [8, 567375],
            [7, 647375],
            [6, 727375],
            [5, 807375],
            [4, 887375],
            [3, 1047375],
            [2, 1207375],
            [1, 1847375],
            [0.5, 2487375],
            [0.25, 3767375],
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
        embed.add_field(name="🇳 🇪 🇹 🇼 🇴 🇷 🇰", value=f"""Global Network Blocks: **{self.blocks}**
Global Network Diff: **{self.difficulty:.2f}**

Global Network Hash: **{normalize_hashrate(self.hashrate)}**
Global Pool Hash: **{normalize_hashrate(sum(self.pools_stat.values()))}**
Expected Global Hash: **{normalize_hashrate((self.hashrate+sum(self.pools_stat.values()))/2)}**""", inline=False)
        unknowhash = self.hashrate - sum(self.pools_stat.values())
        embed.add_field(name="🇵 🇴 🇴 🇱 🇸", value=f"""{f'''
'''.join(f"{pool_icon(pool_hashrate*100/self.hashrate)}<{pool}>: **{normalize_hashrate(pool_hashrate)}** (*{pool_hashrate*100/self.hashrate:.2f}%*)"for pool, pool_hashrate in sorted(self.pools_stat.items(), key=lambda kv: kv[1] or -1))}

❔Unknow pool/Solo hashrate: {f"{normalize_hashrate(unknowhash)} (*{unknowhash*100/self.hashrate:.2f}%*)" if unknowhash > 0 else '---'}""", inline=False)
        embed.set_footer(text=f"Last update: {self.last_pool_update.ctime()}")
        return embed

def getmininginfo():
    try:
        r = requests.post("http://127.0.0.1:8771/", auth=("user","password"), data='{"method": "getmininginfo"}').json()
    except:
        return {}
    return r.get("result") or {}

def getblockreward():
    try:
        return requests.post("http://127.0.0.1:8771/", auth=("user","password"), data='{"method": "getblocksubsidy"}').json()["result"]["miner"]
    except:
        return None

def normalize_hashrate(hashrate):
    if isinstance(hashrate, str):
        return hashrate
    if hashrate is None or hashrate < 0:
        return "unknown"
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