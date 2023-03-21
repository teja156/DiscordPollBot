import discord
from discord.ext import tasks
import datetime as dt
DISCORD_TOKEN = "" # Change this



# Define required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create client object
client = discord.Client(intents=intents)
POLL_OPTION_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

SENT_MESSAGE_IDS = []

@client.event
async def on_message(message):
    global POLL_OPTION_EMOJIS
    if message.content.startswith("!create_poll"):
        # Extract the parameters from the command
        params = message.content.split(";")
        name = params[0].replace("!create_poll","").strip()
        question = params[1].strip()
        options = [x.strip() for x in params[2].strip().split(",")]
        orig_options = options
        options_count = len(options)
        countdown = params[3]

        try:
            countdown = int(countdown)
        except Exception as e:
            pass
        

        # validate parameters to check if there are any errors
        error = validate_params(name, question, options, countdown)

        if error is not None:
            # If parameters are not in the expected format, send error message
            embed = discord.Embed(title="Error", description=error, color=discord.Color.red())
            sent = await message.channel.send(embed=embed)
            return

        # If there is no error, send the poll message
        for i in range(len(options)):
                options[i] = f"{POLL_OPTION_EMOJIS[i]} {options[i]}"
        options = '\n'.join(options)

        embed = discord.Embed(title=f"POLL: {name}", description=f"**{question}\n{options}**", color=0x12ff51)
        sent = await message.channel.send(embed=embed)

        POLL_OPTION_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i in range(options_count):
            # React with the allowed set of emojis
            await sent.add_reaction(POLL_OPTION_EMOJIS[i])
        
        # Add sent message id to a global list
        SENT_MESSAGE_IDS.append(sent.id)
        end_time = dt.datetime.utcnow() + dt.timedelta(seconds=int(countdown)*60)
        # define the background task to update the countdown message
        @tasks.loop(seconds=1)
        async def update_countdown():
            # Calculate remaining time in countdown
            remaining_time = (end_time - dt.datetime.utcnow()).total_seconds()

            if remaining_time > 0:
                # If countdown still didn't expire
                minutes, seconds = divmod(int(remaining_time), 60)

                # Edit the message
                description = f"**{question}**\n{options}\n\n*Poll ends in {minutes:02d}:{seconds:02d}*"
                embed = discord.Embed(title=f"POLL: {name}", description=description, color=0x12ff51)
                await sent.edit(embed=embed)

            else:
                sent_message = await message.channel.fetch_message(sent.id)

                poll_results_count = {}
                total_reactions = 0

                # If countdown expired
                for reaction in sent_message.reactions:
                    # Enumerate message reactions
                    for ind, emoji in enumerate(POLL_OPTION_EMOJIS):
                        # Count number of times an emoji is reacted
                        if reaction.emoji == emoji:
                            poll_results_count[ind+1] = reaction.count - 1
                            if reaction.count>1:
                                # ALso calculate the total reactions
                                total_reactions+=1

                # Craft the results message
                poll_results_message = ""
                for ind, count in enumerate(poll_results_count):
                    # Calculate percentage value of each option                  
                    perc = round(poll_results_count[ind+1]/total_reactions * 100)
                    poll_results_message+=f"{orig_options[ind]} ~ {perc}% ({poll_results_count[ind+1]} votes)\n"
                
                # Send the results message
                embed = discord.Embed(title=f"POLL RESULTS: {name}", description=poll_results_message, color=0x13a6f0)
                await message.channel.send(embed=embed)


                # Delete the original poll message and end tasks.loop function
                await sent_message.delete()
                update_countdown.cancel()
        
        update_countdown.start()


    @client.event
    async def on_raw_reaction_add(payload):
        global SENT_MESSAGE_IDS
        # Get the message object
        channel = await client.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Get the member object
        guild = message.guild
        member = await guild.fetch_member(payload.user_id)

        if payload.member.bot:
            return

        sent_by_bot = False
        for i in SENT_MESSAGE_IDS:
            # Compare message ids
            if i==message.id:
                sent_by_bot = True
                break
        if not sent_by_bot:
            # IF not sent by bot, ignore
            return
        
        # Check if reaction made is allowed
        if payload.emoji.name not in POLL_OPTION_EMOJIS:
            # Remove reaction
            await message.remove_reaction(payload.emoji.name, member)
            return

        # Remove duplicate votes of the user
        user_reaction_count = 0
        for r in message.reactions:
            async for u in r.users():
                if u.id == payload.user_id:
                    user_reaction_count+=1
                    if user_reaction_count>1:
                        await message.remove_reaction(payload.emoji.name, member)
                        break

def validate_params(name, question, options, countdown):
    if name=="":
        return "Poll name shouldn't be empty"
    if len(name)>=20:
        return "Name shouldn't be more than 15 characters"
    if question=="":
        return "Question shouldn't be empty"
    if len(options)<=1:
        return "There must be a minimum of 2 options"
    if len(options)>5:
        return "Maximum options allowed are 5"
    if not isinstance(countdown, int):
        return "Countdown value must be integer"

    return None



if __name__ == "__main__":
    # Start the bot
    client.run(DISCORD_TOKEN)
