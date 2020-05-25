# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import urllib.request, urllib.parse, json
import re
import bot_config
updater = Updater(bot_config.token, use_context=True)
# The main regex we use to find linkable terms in messages
regex = re.compile(r"(\[\[.+?[\||\]]|(?<!\w)(?<!\w[=/])(?<!wiki/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema:)(?<!title=)(L[1-9]\d*(-[SF]\d+)|[QPLE][1-9]\d*(#P\d+)?))")

messages = {
    "start-group": ("🤖 Hello! I am a bot that links [[wiki links]] and Wikidata "
            "entities when they are used in chats. You can "
            "<a href='https://t.me/wikilinksbot'>start a private chat with me</a> "
            "to test me out and learn about how I can be configured."),
    "start-private": ("🤖 Hello! I am a bot that links [[wiki links]] and Wikidata entities "
            "when they are used in chats. I have the following configuration options, "
            "try any of them here to see how they work:\n\n"
            "/setwiki - Change which wiki links point to\n"
            "/setlang - Change which language to use for Wikidata labels\n"
            "/toggle - Turn the two link types on or off\n\n"
            "My source code and documentation is available "
            "<a href='https://github.com/jhsoby/wikilinksbot'>on GitHub</a> – "
            "Feel free to report any issues you may have with me there! 😊"),
    "setwiki_success": "✅ The URL for {0} has been updated to {1} for this chat.",
    "setwiki_error": ("The format for the /setwiki command is:\n"
            "<code>/setwiki (normallinks|wikibaselinks) https://$URL/</code>\n\n"
            "The URL must be the base domain for the wiki, and wikis are assumed "
            "to follow the Wikimedia convention where content is at <code>$URL/wiki/</code> "
            "and the API is available at <code>$URL/w/api.php</code>.\n\n"
            "This will change the link settings for this entire chat, so use with caution."),
    "toggle_success": "✅ Linking of {0} has been turned <b>{1}</b> for this chat.",
    "toggle_error": ("The format for the /toggle command is:\n"
            "<code>/toggle (normallinks|wikibaselinks) (on|off)</code>\n\n"
            "By default both are turned on. If both are turned off, the bot will "
            "in effect be disabled."),
    "setlang_success": "✅ The languages used for labels have now been changed to <code>{0}</code>.",
    "setlang_error": ("The format for the /setlang command is:\n"
            "<code>/setlang language_code</code>\n\n"
            "The language code must be one that is in use in Wikidata, "
            "though the bot makes no attempt to validate the language code "
            "other than a basic regex to check if it could <i>theoretically</i> "
            "be a valid language code. You can also have several languages in preferred order, "
            "just separate them with the <code>|</code> character (a.k.a. pipe).\n\n"
            "You can see a list of valid language codes "
            "<a href='https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=languages'>in "
            "the API</a>."),
    "setlang_invalid": ("<b>Error:</b> The language code <code>{0}</code> does not look like a valid "
                        "language code. Please fix it and try again.\n\n"),
    "config_error": "Invalid use of the <code>{}</code> command. Use /help for a list of commands for this bot and how to use them.",
    "permission_error": ("⛔️ Sorry, you do not have permission to change the bot configuration in this "
                 "chat. Only group administrators or the bot's maintainers may change the configuration.")
}

def labelfetcher(item, languages, wb, sep_override="–"):
    """
    Gets the label from the Wikidata items/properties in question, in the
    language set in the configuration, with a fallback to English, or gets
    the lemma and language code for lexemes.
    Returns False if there is no label.
    """
    if not item:
        return False
    if item[0] in ["Q", "P"]: # Is the entity an item or property?
        with urllib.request.urlopen(wb + "w/api.php?action=wbgetentities&languages=" + languages + "&props=labels&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            sep = sep_override
            if item[0] == "Q":
                with urllib.request.urlopen(wb + "w/api.php?action=wbgetclaims&entity=" + item + "&property=P487&format=json") as emoji:
                    emojidata = json.loads(emoji.read().decode())
                    if "claims" in emojidata:
                        if "P487" in emojidata["claims"]:
                            if emojidata["claims"]["P487"][0]["mainsnak"]["snaktype"] == "value":
                                sep = emojidata["claims"]["P487"][0]["mainsnak"]["datavalue"]["value"]
            try:
                languages = (languages + "|en").split("|")
                for lang in languages:
                    if lang in data["entities"][item]["labels"]:
                        label = data["entities"][item]["labels"][lang]["value"]
                        if not lang == languages[0]:
                            label = label + " [<code>" + lang + "</code>]"
                        if label == sep:
                            sep = sep_override
                        return sep + " " + label
            except:
                return False
    elif item[0] == "L": # Is the item a lexeme?
        with urllib.request.urlopen(wb + "w/api.php?action=wbgetentities&props=info&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            try:
                for lang in data["entities"][item]["lemmas"]:
                    lemma = data["entities"][item]["lemmas"][lang]["value"]
                    language = data["entities"][item]["lemmas"][lang]["language"]
                    label = lemma + " [<code>" + language + "</code>]"
                    return label
            except:
                return False
    return False

def resolveredirect(link, url):
    """
    Checks [[normal links]] for whether or not they are redirects, and gets
    the target title for the redirect page.
    """
    target = link
    with urllib.request.urlopen(url + "w/api.php?action=query&titles=" + urllib.parse.quote(link) + "&redirects=1&format=json") as apiresult:
        api = json.loads(apiresult.read().decode())["query"]
        if "redirects" in api:
            target = api["redirects"][0]["to"]
    if link == target:
        return False
    else:
        return target

def linkformatter(link, conf):
    """
    Formats a single link in the correct way.
    """
    section = False
    display = link
    url = link
    formatted = "<a href='{0}'>{1}</a> {2}"
    if re.match(r"[QLP]\d+#P\d+", link):
        link, section = link.split("#")
    elif re.match(r"L\d+-[SF]\d+", link):
        link, section = link.split("-")
        display = link + "-" + section
        url = link + "#" + section
    linklabel = labelfetcher(link, conf["language"], conf["wikibaselinks"])
    if section:
        sectionlabel = (labelfetcher(section, conf["language"], conf["wikibaselinks"], sep_override=" →") or " → " + section)
    prefixes = {
        "Q": "",
        "P": "Property:",
        "L": "Lexeme:",
        "E": "EntitySchema:"
    }
    if (link[-1] == "|" or link[-1] == "]") and conf["toggle_normallinks"]:
        link = re.sub(r"[\[\]\|]", "", display)
        display = "&#91;&#91;" + link + "&#93;&#93;"
        url = conf["normallinks"] + "wiki/" + link.replace(" ", "_")
        redirect = resolveredirect(link, conf["normallinks"])
        if redirect:
            url = conf["normallinks"] + "wiki/" + redirect.replace(" ", "_")
            return formatted.format(url, display, "⮡ " + redirect)
        else:
            return formatted.format(url, display, "")
    elif (link[0] in "QPLE") and conf["toggle_wikibaselinks"]:
        url = conf["wikibaselinks"] + "wiki/" + prefixes[link[0]] + url
        if section:
            if linklabel:
                linklabel += sectionlabel
            else:
                linklabel = sectionlabel
        if linklabel:
            return formatted.format(url, display, linklabel)
        else:
            return formatted.format(url, display, "")
    else:
        return False

def link(update, context):
    """
    Finds all potential links in a message. The regex looks for [[links]],
    including [[links|like this]], and Wikidata entities just casually mentioned.
    The Wikidata entity types that are supported are items, properties, lexemes
    and entity schemas. It will however _not_ post a link when the entity is
    mentioned as part of a URL.
    """
    linklist = re.findall(regex, update.message.text)
    fmt_linklist = []
    for link in linklist:
        link = linkformatter(link[0], getconfig(update.effective_chat.id))
        if link and (not link in fmt_linklist):
            fmt_linklist.append(link)
    if len(fmt_linklist) > 0:
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(fmt_linklist), disable_web_page_preview=True, disable_notification=True, parse_mode="html")

def getconfig(chat_id):
    """
    Checks if there is any group configuration for this group in group_settings.json,
    and overrides the defaults (conf) with what's in the config file.
    """
    chat_id = str(chat_id)
    conf = {
        "normallinks": "https://en.wikipedia.org/",
        "wikibaselinks": "https://www.wikidata.org/",
        "toggle_normallinks": True,
        "toggle_wikibaselinks": True,
        "language": "en"
    }
    with open("group_settings.json", "r") as settings:
        settings = json.load(settings)
        if chat_id in settings:
            for x in settings[chat_id]:
                conf[x] = settings[chat_id][x]
    return conf

def config(update, context):
    """
    Function for various configuration commands that can be made by the bot.
    """
    # Only allow group administrators and bot maintainers (configured in bot_config.py)
    # to make configuration changes to the bot, except for one-on-one chats with the bot.
    allow = False
    if (context.bot.get_chat_member(update.effective_chat.id, update.message.from_user.id).status in ["administrator", "creator"]) or (str(update.message.from_user.id) in bot_config.superusers) or (update.effective_chat.type == "private"):
        allow = True
    if not allow:
        update.message.reply_text(text=messages["permission_error"])
        return
    message = update.message.text.split()
    chat_id = str(update.effective_chat.id)
    # Commands can be done either as /command or /command@botname.
    # If done in the latter way, we only want to use what's before the @.
    command = message[0].split("@")[0]
    # TODO: This if/elif block can probably be condensed quite a bit.
    if command == "/setwiki" and len(message) >= 3:
        option = message[1]
        options = {"normallinks": "normal [[wiki links]]", "wikibaselinks": "Wikibase entity links"}
        wikiurl = message[2]
        if option in options and re.match(r"https?:\/\/\w+(\.\w+)*?\/", wikiurl):
            with open("group_settings.json", "r+") as f:
                settings = json.load(f)
                if chat_id in settings:
                    settings[chat_id][option] = wikiurl
                else:
                    settings[chat_id] = {option: wikiurl}
                f.seek(0)
                json.dump(settings, f, indent=4)
                f.truncate()
            successtext = messages["setwiki_success"].format(options[option], wikiurl)
            update.message.reply_text(text=successtext, disable_web_page_preview=True)
        else:
            update.message.reply_text(text=messages["setwiki_error"], parse_mode="html")
    elif command == "/toggle" and len(message) >= 3:
        option = "toggle_" + message[1]
        options = {"toggle_normallinks": "normal [[wiki links]]", "toggle_wikibaselinks": "Wikibase entity links"}
        toggle = message[2]
        toggles = {"on": True, "off": False}
        if option in options and toggle in ["on", "off"]:
            with open("group_settings.json", "r+") as f:
                settings = json.load(f)
                if chat_id in settings:
                    settings[chat_id][option] = toggles[toggle]
                else:
                    settings[chat_id] = {option: toggles[toggle]}
                f.seek(0)
                json.dump(settings, f, indent=4)
                f.truncate()
            successtext = messages["toggle_success"].format(options[option], toggle)
            update.message.reply_text(text=succestext, parse_mode="html")
        else:
            update.message.reply_text(text=messages["toggle_error"], parse_mode="html")
    elif command == "/setlang" and len(message) >= 2:
        languages = message[1] + "|en"
        error = False
        for lang in languages.split("|"):
            if not re.match(r"^([a-z]{2,3}(-[a-z]+)*?|es-419)$", lang):
                error = lang
                break
        if error != False:
            errortext = messages["setlang_invalid"].format(error) + messages["setlang_error"]
            update.message.reply_text(text=errortext, parse_mode="html")
        else:
            with open("group_settings.json", "r+") as f:
                settings = json.load(f)
                if chat_id in settings:
                    settings[chat_id]["language"] = languages
                else:
                    settings[chat_id] = {"language": languages}
                f.seek(0)
                json.dump(settings, f, indent=4)
                f.truncate()
            successtext = messages["setlang_success"].format(languages)
            update.message.reply_text(text=successtext, parse_mode="html")
    else:
        errortext = messages[command[1:] + "_error"]
        update.message.reply_text(text=errortext, parse_mode="html")

def start(update, context):
    """
    Start command that should be part of every Telegram bot.
    Also used for the /help command.
    """
    message = "start-group"
    if update.effective_chat.type == "private":
        message = "start-private"
    context.bot.send_message(chat_id=update.effective_chat.id, text=messages[message], parse_mode="html", disable_web_page_preview=True)

# Function used when testing changes to the bot. Uncomment to enable.
#def echo(update, context):
#    print(update.effective_chat.type)
#    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
#echo_handler = CommandHandler('echo', echo)
#updater.dispatcher.add_handler(echo_handler)


link_handler = MessageHandler(Filters.regex(regex), link)
config_handler = CommandHandler(['setwiki', 'setlang', 'toggle'], config)
start_handler = CommandHandler(['start', 'help'], start)

updater.dispatcher.add_handler(link_handler)
updater.dispatcher.add_handler(config_handler)
updater.dispatcher.add_handler(start_handler)
try:
    updater.start_polling()
    updater.idle()
except KeyboardInterrupt:
    updater.stop()
