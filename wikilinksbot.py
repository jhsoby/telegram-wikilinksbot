# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import urllib.request, json
import re
import bot_config
updater = Updater(bot_config.token, use_context=True)

def labelfetcher(item):
    """
    Gets the English-language label from the Wikidata items/properties in
    question, or the lemma and language code for lexemes.
    Returns False if there is no label in English.
    """
    if item[0] in ["P", "Q"]:
        with urllib.request.urlopen("https://www.wikidata.org/w/api.php?action=wbgetentities&languages=en&props=labels&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            try:
                # TODO: Make the language fetched configurable for each Telegram group
                label = data["entities"][item]["labels"]["en"]["value"]
                return label
            except:
                return False
    if item[0] == "L":
        with urllib.request.urlopen("https://www.wikidata.org/w/api.php?action=wbgetentities&props=info&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            try:
                for lang in data["entities"][item]["lemmas"]:
                    lemma = data["entities"][item]["lemmas"][lang]["value"]
                    language = data["entities"][item]["lemmas"][lang]["language"]
                    label = lemma + " (<code>" + language + "</code>)"
                    return label
            except:
                return False

def linkformatter(link):
    """
    Formats a single link in the correct way.
    """
    # TODO: Figure out how to make these four variables configurable per
    # group in Telegram.
    normallink = "https://en.wikipedia.org/wiki/"
    normallink_toggle = True
    wikibaselink = "https://www.wikidata.org/wiki/"
    wikibaselink_toggle = True
    display = link
    url = link
    label = False
    if normallink_toggle:
        if link[-1] == "|" or link[-1] == "]":
            link = re.sub(r"[\[\]\|]", "", display)
            display = "[[" + link + "]]"
            url = normallink + link.replace(" ", "_")
    if wikibaselink_toggle:
        if link[0] == "Q":
            url = wikibaselink + display
            label = labelfetcher(link)
        elif link[0] == "P":
            url = wikibaselink + "Property:" + display
            label = labelfetcher(link)
        elif link[0] == "L":
            url = wikibaselink + "Lexeme:" + display
            label = labelfetcher(link)
        elif link[0] == "E":
            url = wikibaselink + "EntitySchema:" + display
    display = display.replace("[", "&#91;").replace("]", "&#93;")
    formatted = "<a href='" + url + "'>" + display + "</a>"
    if label:
        return formatted + " – " + label
    else:
        return formatted

def linker(messagetext):
    """
    Finds all potential links in a message. The regex looks for [[links]],
    including [[links|like this]], and Wikidata entities just casually mentioned.
    The Wikidata entity types that are supported are items, properties, lexemes
    and entity schemas. It will however _not_ post a link when the entity is
    mentioned as part of a URL.
    """
    linklist = re.findall(r'(\[\[.+?[\||\]]|(?<!wiki/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema)(?<!title=)[QPLE]\d+)', messagetext)
    fmt_linklist = []
    for link in linklist:
        link = linkformatter(link)
        if not link in fmt_linklist:
            fmt_linklist.append(link)
    return "\n".join(fmt_linklist)

def link(update, context):
    """
    Does the actualy sending of the message.
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=linker(update.message.text), disable_web_page_preview=True, disable_notification=True, parse_mode='html')

# Same regex as above; if there are hits on this regex, the bot knows that it
# needs to do something.
link_handler = MessageHandler(Filters.regex(r'(\[\[.+?[\||\]]|(?<!wiki/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema)(?<!title=)[QPLE]\d+)'), link)

updater.dispatcher.add_handler(link_handler)
updater.start_polling()
