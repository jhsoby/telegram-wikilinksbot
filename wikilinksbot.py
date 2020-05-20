# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import urllib.request, json
import re
import bot_config
updater = Updater(bot_config.token, use_context=True)

messages = {
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
    "setlang_success": "✅ The language used for labels has now been changed to <code>{0}</code>.",
    "setlang_error": ("The format for the /setlang command is:\n"
                 "<code>/setlang language_code</code>\n\n"
                 "The language code must be one that is in use in Wikidata, "
                 "though the bot makes no attempt to validate the language code "
                 "other than a basic regex to check if it could <i>theoretically</i> "
                 "be a valid language code.\n\n"
                 "You can see a list of valid language codes <a href='https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=languages'>in the API</a>."),
    "config_error": "Invalid use of the <code>{}</code> command. Use /help for a list of commands for this bot and how to use them.",
    "permission_error": ("⛔️ Sorry, you do not have permission to change the bot configuration in this "
                 "chat. Only group administrators or the bot's maintainers may change the configuration.")
}

def labelfetcher(item, lang, wb):
    """
    Gets the label from the Wikidata items/properties in question, in the
    language set in the configuration, with a fallback to English, or gets
    the lemma and language code for lexemes.
    Returns False if there is no label.
    """
    if item[0] in ["Q", "P"]: # Is the entity an item or property?
        with urllib.request.urlopen(wb + "w/api.php?action=wbgetentities&languages=" + lang + "|en&props=labels&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            try:
                if lang in data["entities"][item]["labels"]:
                    label = data["entities"][item]["labels"][lang]["value"]
                else:
                    label = data["entities"][item]["labels"]["en"]["value"] + " [<code>en</code>]"
                return label
            except:
                return False
    if item[0] == "L": # Is the item a lexeme?
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

def linkformatter(link, conf):
    """
    Formats a single link in the correct way.
    """
    display = link
    url = link
    formatted = "<a href='{0}'>{1}</a> {2}"
    label = False
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
        return formatted.format(url, display, "")
    elif (link[0] in "QPLE") and conf["toggle_wikibaselinks"]:
        url = conf["wikibaselinks"] + "wiki/" + prefixes[link[0]] + display
        label = labelfetcher(link, conf["language"], conf["wikibaselinks"])
        if label:
            return formatted.format(url, display, "– " + label)
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
    linklist = re.findall(r'(\[\[.+?[\||\]]|(?<!wiki/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema:)(?<!title=)[QPLE][1-9]\d*)', update.message.text)
    fmt_linklist = []
    for link in linklist:
        link = linkformatter(link, getconfig(update.effective_chat.id))
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
        language = message[1]
        if re.match(r"^([a-z]{2,3}(-[a-z]+)*?|es-419)$", language):
            with open("group_settings.json", "r+") as f:
                settings = json.load(f)
                if chat_id in settings:
                    settings[chat_id]["language"] = language
                else:
                    settings[chat_id] = {"language": language}
                f.seek(0)
                json.dump(settings, f, indent=4)
                f.truncate()
            successtext = messages["setlang_success"].format(language)
            update.message.reply_text(text=successtext, parse_mode="html")
        else:
            update.message.reply_text(text=messages["setlang_error"], parse_mode="html")
    else:
        errortext = messages[command[1:] + "_error"]
        update.message.reply_text(text=errortext, parse_mode="html")

# Same regex as above in the function "link"; if there are hits on this regex,
# the bot knows that it needs to do something.
link_handler = MessageHandler(Filters.regex(r'(\[\[.+?[\||\]]|(?<!wiki/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema:)(?<!title=)[QPLE][1-9]\d*)'), link)
setwiki_handler = CommandHandler('setwiki', config)
setlang_handler = CommandHandler('setlang', config)
toggle_handler = CommandHandler('toggle', config)

updater.dispatcher.add_handler(link_handler)
updater.dispatcher.add_handler(setwiki_handler)
updater.dispatcher.add_handler(setlang_handler)
updater.dispatcher.add_handler(toggle_handler)
updater.start_polling()
