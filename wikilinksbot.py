# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import urllib.request, urllib.parse, json
import random
import re
import gc
import bot_config

gc.enable()
updater = Updater(bot_config.token, use_context=True)
# The main regex we use to find linkable terms in messages
regex = re.compile(r"(\[\[.+?\]\]|(?<!\{)\{\{(?!\{).+?\}\}|(?<![\w%.])(?<![A-Za-z][=/])(?<!^/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema:)(?<!Item:)(?<!title=)(L[1-9]\d*(-[SF]\d+)|[QPLEM][1-9]\d*(#P[1-9]\d*)?(@\w{2,3}(-\w{2,4}){0,2})?|T[1-9]\d*(#[1-9]\d*)?))")

# Load the group settings file once for every time the script is run.
# If any settings change, global_conf will be set again.
global_conf = {}
with open("group_settings.json", "r") as settings:
    global_conf = json.load(settings)

messages = {
    "start-group": ("🤖 Hello! I am a bot that links [[wiki links]], Wikidata "
            "entities and optionally Phabricator tasks when they are mentioned in chats. You can "
            "<a href='https://t.me/wikilinksbot'>start a private chat with me</a> "
            "to test me out and learn about how I can be configured. If you don't "
            "like one of my messages, reply to it with <code>/delete</code>."),
    "start-private": ("🤖 Hello! I am a bot that links [[wiki links]], Wikidata entities "
            "and Phabricator tasks "
            "when they are mentioned in chats. I have the following configuration options, "
            "try any of them here to see how they work:\n\n"
            "/setwiki – Change which wiki links point to\n"
            "/setlang – Change which language to use for Wikidata labels\n"
            "/toggle – Turn the link types on or off\n"
            "/listconfig – Show the current configuration for this chat\n\n"
            "If you don't like one of my messages, reply to it with <code>/delete</code>, "
            "and I will delete it. If I'm made administrator in a group, I will delete "
            "your <code>/delete</code> message as well!\n\n"
            "My source code and documentation is available "
            "<a href='https://github.com/jhsoby/wikilinksbot'>on GitHub</a> – "
            "Feel free to report any issues you may have with me there! 😊"
            "If you just have some questions, feel free to ask my creator, @jhsoby."),
    "setwiki_success": "✅ The URL for {0} has been updated to {1} for this chat.",
    "setwiki_invalid": ("❌ I am not able to recognize that URL as a MediaWiki wiki.\n\n"
            "Please check that you entered the URL correctly. If you believe this "
            "is an error in the bot, please feel free to "
            "<a href=\"https://github.com/jhsoby/telegram-wikilinksbot/issues/new\">report it</a>."),
    "setwiki_error": ("The format for the /setwiki command is:\n"
            "<code>/setwiki (normallinks|wikibaselinks) https://$URL</code>\n\n"
            "The URL has to be a wiki, and it has to be openly accessible on "
            "the web.\n\n"
            "This will change the link settings for this entire chat, so use with caution."),
    "toggle_success": "✅ Linking of {0} has been turned <b>{1}</b> for this chat.",
    "toggle_error": ("The format for the /toggle command is:\n"
            "<code>/toggle (normallinks|wikibaselinks|phabricator|mylanguage|templates) (on|off)</code>\n\n"
            "By default all are turned on. If all are turned off, "
            "the bot will in effect be disabled."),
    "setlang_success": "✅ The language priority list for labels has now been changed to <code>{0}</code>.",
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
            "chat. Only group administrators or the bot's maintainers may change the configuration."),
    "delete_error": ("There's nothing I can delete. <b>Reply</b> to any of my messages "
            "(including this one) with <code>/delete</code> to delete that message."),
    "search_nothing": ("🤖 You gotta give me something to work with here! Type <code>/search</code> "
            "followed by what you want to search for."),
    "search_noresults": "🔎 No <a href=\"{0}\">results</a>. 😔",
    "search_oneresult": "🔎 <b>Only</b> <a href=\"{0}\">result</a>:\n",
    "search_allresults": "🔎 All <b>{0}</b> <a href=\"{1}\">results</a>:\n",
    "search_results": "🔎 First <b>{0}</b> of <a href=\"{2}\">{1} results</a>:\n"
}

def labelfetcher(item, languages, wb, sep_override="–", force_lang=""):
    """
    Gets the label from the Wikidata items/properties in question, in the
    language set in the configuration, with a fallback to English, or gets
    the lemma and language code for lexemes.
    Returns False if there is no label.
    """
    if not item:
        return False
    if force_lang:
        force_lang = force_lang + "|"
    if item[0] in ["Q", "P"]: # Is the entity an item or property?
        with urllib.request.urlopen(wb["baseurl"] + wb["apipath"] + "?action=wbgetentities&props=labels&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            sep = sep_override
            if item[0] == "Q" and wb["baseurl"] == "https://www.wikidata.org": # Easter egg! Check if the item has P487 (normally an emoji) set, and use that instead of the separator if there is one.
                with urllib.request.urlopen(wb["baseurl"] + wb["apipath"] + "?action=wbgetclaims&entity=" + item + "&property=P487&format=json") as emoji:
                    emojidata = json.loads(emoji.read().decode())
                    if "claims" in emojidata:
                        if "P487" in emojidata["claims"]:
                            if emojidata["claims"]["P487"][0]["mainsnak"]["snaktype"] == "value":
                                sep = emojidata["claims"]["P487"][0]["mainsnak"]["datavalue"]["value"]
            try:
                present_labels = data["entities"][item]["labels"] # All labels for the item
                priority_languages = (force_lang + languages + "|en").split("|") # Languages for the chat, set by /setlang
                labellang = random.choice(list(present_labels)) # Choose a random language from the present labels
                for lang in priority_languages[::-1]: # Go through the list of priority languages from the back, and set whatever language that has a label as the label instead of the randomly chosen one
                    if lang in present_labels:
                        labellang = lang
                label = present_labels[labellang]["value"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if not labellang == priority_languages[0]: # If the final label language is not the first in the priority list, attach the language code for the chosen label
                    label += " [<code>" + labellang + "</code>]"
                if (
                    label == sep
                    or (len(sep) == 1 and ord(sep) < 128)
                    or re.match(r"\w", sep)
                ): # Check if the emoji is probably an emoji, and not some other character
                    sep = sep_override
                return sep + " " + label
            except:
                return False
    elif item[0] == "L": # Is the item a lexeme?
        with urllib.request.urlopen(wb["baseurl"] + wb["apipath"] + "?action=wbgetentities&props=info&format=json&ids=" + item) as url:
            data = json.loads(url.read().decode())
            labels = []
            try:
                lemmas = data["entities"][item]["lemmas"]
                for lang in lemmas:
                    lemma = data["entities"][item]["lemmas"][lang]["value"]
                    language = data["entities"][item]["lemmas"][lang]["language"]
                    label = lemma + " [<code>" + language + "</code>]"
                    labels.append(label)
                return sep_override + " " + " / ".join(labels)
            except:
                return False
    elif item[0] == "M": # Is the item a media item?
        with urllib.request.urlopen("https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&props=info&ids=" + item) as url:
            data = json.loads(url.read().decode())
            try:
                label = data["entities"][item]["title"]
                return sep_override + " " + label
            except:
                return False
    elif item[0] == "E": # Is the item an EntitySchema?
        # Should be replaced when EntitySchemas' terms are more
        # readily accessible via the API.
        language = languages.split("|")[0]
        with urllib.request.urlopen(wb["baseurl"] + wb["apipath"] + "?format=json&action=parse&uselang=" + language + "&page=EntitySchema:" + item) as url:
            data = json.loads(url.read().decode())
            try:
                title = data["parse"]["displaytitle"]
                label = re.search(r"<span class=\"entityschema-title-label\">([^<]+)</span>", title).group(1)
                return sep_override + " " + label
            except:
                return False
    elif item[0] == "T": # Is the "item" actually a Phabricator task?
        with urllib.request.urlopen("https://phabricator.wikimedia.org/api/maniphest.search?api.token=" + bot_config.phabtoken + "&limit=1&constraints[ids][0]=" + item[1:]) as url:
            data = json.loads(url.read().decode())
            try:
                title = data["result"]["data"][0]["fields"]["name"]
                status = data["result"]["data"][0]["fields"]["status"]["name"].lower()
                label = title + " <code>[" + status + "]</code>"
                return sep_override + " " + label
            except:
                return False
    return False

def resolvetarget(site, link):
    """
    Checks [[normal links]] for whether or not they are redirects and whether
    or not they are interwiki links.
    
    Returns a list where the first item is the domain to link to, the second is
    the link title, the third is a boolean of whether or not the target site
    is a wiki, and the fourth is False if the page is not a redirect, or the
    redirect target if the page is a redirect.
    """
    target = link
    domain = site["baseurl"]
    if not len(link):
        return [domain, link, False, False]
    if link[0] == ":":
        link = link[1:]
    linksplit = link.split(":")
    with urllib.request.urlopen(site["baseurl"] + site["apipath"] + "?format=json&action=query&iwurl=1&redirects=1&titles=" + urllib.parse.quote(link)) as apiresult:
        api = json.loads(apiresult.read().decode())["query"]
        if "redirects" in api:
            target = api["redirects"][0]["to"]
            if target == link:
                return [domain, link, True, False]
            else:
                return [domain, link, True, target]
        elif "normalized" in api:
            target = api["normalized"][0]["to"]
            return [domain, target, True, False]
        elif "interwiki" in api:
            url_from_api = api["interwiki"][0]["url"]
            domainsplit = url_from_api.split("/")
            domain = "/".join(domainsplit[:3])
            link = ":".join(linksplit[1:])
            if domainsplit[3] == "wiki":
                return resolvetarget({"baseurl": domain, "apipath": "/w/api.php"}, link)
            else:
                parsed_link = urllib.parse.quote(link.replace(" ", "_"))
                urlsplit = url_from_api.split(parsed_link)
                domain = urlsplit[0]
                link = link + urlsplit[1]
                return [domain, link, False, False]
        else:
            return [domain, link, True, False]

def translatable(domain, link):
    """
    Checks whether or not a page is translatable (thus whether or not it makes
    sense to add Special:MyLanguage in front of it).

    (This API call could be improved if T265974 is acted upon.)
    """
    with urllib.request.urlopen(domain["baseurl"] + domain["apipath"] + "?format=json&action=parse&prop=modules|jsconfigvars&page=" + urllib.parse.quote(link)) as apiresult:
        try:
            api = json.loads(apiresult.read().decode())
        except:
            return False
        else:
            if ("parse" in api) and ("ext.translate" in api["parse"]["modulestyles"]):
                return True
            else:
                return False
    return False

def link_normal(link, site, toggle_mylang=False):
    """
    Handles [[normal]] wiki links
    """
    target = re.sub(r"[\[\]]", "", link)
    target = target.split("|")[0]
    display = "&#91;&#91;" + target + "&#93;&#93;"
    extra = ""
    domain, target, iswiki, redirect = resolvetarget(site, target)
    if iswiki:
        if redirect:
            target = redirect
            extra = "⮡ " + redirect
        if toggle_mylang and translatable(site, target):
            target = "Special:MyLanguage/" + target
        domain += site["articlepath"]
    target = target.replace("\"", "%22").replace("?", "%3F").replace(" ", "_")
    return {
        "url": domain + target,
        "display": display,
        "extra": extra
    }

def link_template(link, site):
    """
    Handles {{template}} links
    """
    target = re.sub(r"[\{\}]", "", link)
    target = target.split("|")[0]
    targetsplit = target.split(":")
    targetsplit[0] = targetsplit[0].lower().strip()
    display = "&#123;&#123;" + target + "&#125;&#125;"
    extra = ""
    namespaces = []
    with urllib.request.urlopen(site["baseurl"] + site["apipath"] + "?format=json&action=query&meta=siteinfo&siprop=functionhooks|variables|namespaces") as apiresult:
        api = json.loads(apiresult.read().decode())["query"]
        varfuncs = api["functionhooks"] + api["variables"]
        if "special" in varfuncs:
            varfuncs.remove("special")
        apinamespaces = api["namespaces"]
        for ns in apinamespaces:
            if ns != "0":
                namespaces.append(apinamespaces[ns]["canonical"].lower())
                namespaces.append(apinamespaces[ns]["*"].lower())
    if (targetsplit[0] == "#invoke") and (len(targetsplit) > 1):
        target = "Module:" + "".join(targetsplit[1:])
    elif targetsplit[0] == "subst":
        target = "Template:" + "".join(targetsplit[1:])
    elif targetsplit[0] == "int":
        target = "MediaWiki:" + "".join(targetsplit[1:])
    elif ("#" in target) or (targetsplit[0] in varfuncs):
        return False
    elif ((targetsplit[0].lower() in namespaces) and (len(targetsplit) > 1)) or (target[0] == ":"):
        target = target
    else:
        target = "Template:" + target
    resolvedlink = resolvetarget(site, target)
    target = resolvedlink[1]
    redirect = resolvedlink[3]
    if redirect:
        target = redirect
        extra = "⮡ " + redirect
    target = target.replace("\"", "%22").replace("?", "%3F").replace(" ", "_")
    return {
        "url": site["baseurl"] + site["articlepath"] + target,
        "display": display,
        "extra": extra
    }

def link_item(link, site, langconf):
    result = {}
    section = False
    sectionlabel = False
    force_lang = ""
    display = link
    target = link
    if re.match(r"[QLPM]\d+#P\d+", link):
        link, section  = link.split("#")
        sectionlabel = True
    elif re.match(r"L\d+-[SF]\d+", link):
        link, section = link.split("-")
        display = link + "-" + section
        target = link + "#" + section
        sectionlabel = True
    elif re.match(r"T\d+#\d+", link):
        link, section = link.split("#")
    elif ("@" in link):
        link, force_lang = link.split("@")
        display = link
        target = link
        result["force_lang"] = force_lang
    linklabel = labelfetcher(link, langconf, site, force_lang=force_lang)
    if sectionlabel:
        sectionlabel = (labelfetcher(section, langconf, site, sep_override=" →") or " → " + section)
    if section:
        if linklabel:
            linklabel += sectionlabel
        else:
            linklabel = sectionlabel
    if link[0] == "M":
        result["url"] = "https://commons.wikimedia.org/entity/" + target
    elif link[0] == "T":
        result["url"] = "https://phabricator.wikimedia.org/" + target
    elif link[0] == "E":
        result["url"] = site["baseurl"] + "/wiki/EntitySchema:" + target
    else:
        result["url"] = site["baseurl"] + site["entitypath"] + target
    result["display"] = display
    result["extra"] = (linklabel or "")
    return result

def linkformatter(link, conf):
    """
    Formats a single link in the correct way.
    """
    formatted = "<a href=\"{0[url]}\">{0[display]}</a> {0[extra]}"
    formatted_at = "<a href=\"{0[url]}\">{0[display]}</a><code>@{0[force_lang]}</code> {0[extra]}"
    if (link[0] == "[") and conf["toggle_normallinks"]:
        return formatted.format(link_normal(link, conf["normallinks"], conf["toggle_mylanguage"]))
    if (link[0] == "{") and conf["toggle_templates"]:
        linkhandler = link_template(link, conf["normallinks"])
        if linkhandler:
            return formatted.format(linkhandler)
        else:
            return False
    elif (link[0] in "QPLE") and conf["toggle_wikibaselinks"]:
        linkhandler = link_item(link, conf["wikibaselinks"], conf["language"])
        if "force_lang" in linkhandler:
            return formatted_at.format(linkhandler)
        else:
            return formatted.format(linkhandler)
    elif (link[0] == "M") and conf["toggle_wikibaselinks"]: # should have its own toggle
        return formatted.format(link_item(link, conf["wikibaselinks"], conf["language"]))
    elif (link[0] == "T") and conf["toggle_phabricator"]: # Is the link to a Phabricator task?
        return formatted.format(link_item(link, conf["wikibaselinks"], conf["language"]))
    else:
        return False

def findlinks(update, context):
    """
    Finds all potential links in a message. The regex looks for [[links]],
    including [[links|like this]], and Wikidata entities just casually mentioned.
    The Wikidata entity types that are supported are items, properties, lexemes
    and entity schemas. It will however _not_ post a link when the entity is
    mentioned as part of a URL.
    """
    linklist = re.findall(regex, update.message.text) # List all matches with the main regex
    fmt_linklist = [] # Formatted link list
    for link in linklist:
        link = link[0].replace("\u200e", "").replace("\u200f", "") # Remove &lrm; and &rlm;, cause links to not link in some (mysterious?) circumstances
        link = linkformatter(link, getconfig(update.effective_chat.id))
        if link and (not link in fmt_linklist): # Add the formatted link to the list if it's not already there
            fmt_linklist.append(link)
    if len(fmt_linklist) > 0:
        context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(fmt_linklist), disable_web_page_preview=True, disable_notification=True, parse_mode="html")

def search(update, context):
    """
    Search feature. Searches for any query after the `/search` command. Default
    amount of results returned is 3; optionally supply a number with `/search:x`
    to return a different number of results.
    """
    conf = getconfig(update.effective_chat.id)
    numbertosearchfor = 3
    message = update.message.text.split(" ", 1)
    returnmessage = ""
    if len(message) == 1:
        reply = messages["search_nothing"]
        update.message.reply_html(text=reply)
    else:
        command, query = message
        commandsplit = command.split(":")
        resulturl = conf["normallinks"]["baseurl"] + conf["normallinks"]["articlepath"] + "Special:Search/" + urllib.parse.quote(query)
        if len(commandsplit) > 1:
            try:
                numbertosearchfor = int(commandsplit[1])
                if numbertosearchfor > 10:
                    numbertosearchfor = 10
            except:
                pass
        with urllib.request.urlopen(conf["normallinks"]["baseurl"] + conf["normallinks"]["apipath"] + "?format=json&action=query&list=search&srprop=&srlimit=" + str(numbertosearchfor) + "&srsearch=" + urllib.parse.quote(query)) as apiresult:
            api = json.loads(apiresult.read().decode())["query"]
            totalhits = api["searchinfo"]["totalhits"]
            results = []
            for hit in api["search"]:
                hittitle = hit["title"]
                if (conf["normallinks"]["baseurl"] == "https://www.wikidata.org") and (hit["ns"] in [0, 120, 146]):
                    hittitle = re.sub(r"(Property|Lexeme):", "", hittitle)
                else:
                    hittitle = "[[" + hittitle + "]]"
                results.append(linkformatter(hittitle, conf))
            if totalhits < numbertosearchfor:
                numbertosearchfor = totalhits
            elif numbertosearchfor < 1:
                numbertosearchfor = 1
            if totalhits == 0:
                returnmessage = messages["search_noresults"].format(resulturl)
                update.message.reply_html(text=returnmessage, disable_web_page_preview=True)
            elif totalhits == 1:
                returnmessage = messages["search_oneresult"].format(resulturl)
            elif numbertosearchfor == totalhits:
                returnmessage = messages["search_allresults"].format(totalhits, resulturl)
            else:
                returnmessage = messages["search_results"].format(numbertosearchfor, totalhits, resulturl)
            returnmessage += " • " + "\n • ".join(results)
            if totalhits != 0:
                update.message.reply_html(text=returnmessage, disable_web_page_preview=True)

def getconfig(chat_id):
    """
    Checks if there is any group configuration for this group in group_settings.json,
    and overrides the defaults (conf) with what's in the config file.
    """
    chat_id = str(chat_id)
    conf = { # Default configuration
        "normallinks": {
            "baseurl": "https://en.wikipedia.org",
            "articlepath": "/wiki/",
            "apipath": "/w/api.php"
            },
        "wikibaselinks": {
            "baseurl": "https://www.wikidata.org",
            "entitypath": "/entity/",
            "apipath": "/w/api.php"
            },
        "toggle_normallinks": True,
        "toggle_wikibaselinks": True,
        "toggle_phabricator": True,
        "toggle_mylanguage": True,
        "toggle_templates": True,
        "language": "en"
    }
    if chat_id in global_conf:
        for x in global_conf[chat_id]:
            conf[x] = global_conf[chat_id][x]
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
        inputurl = message[2]
        if (option not in options) or not inputurl.startswith("http"):
            update.message.reply_html(text=messages["setwiki_error"])
        else:
            inputurl = re.sub(r"/$", "", inputurl)
            articlepath = "/wiki/"
            validurlentered = False
            for wikiurl in [inputurl + articlepath, inputurl + "/", inputurl.rpartition("/")[0] + "/", inputurl.rpartition("=")[0] + "="]:
                try:
                    urlblob = "Special:ExpandTemplates?wpInput=(articlepath:{{ARTICLEPATH}})(scriptpath:{{SCRIPTPATH}})"
                    if "?" in wikiurl:
                        urlblob = urlblob.replace("?", "&")
                    with urllib.request.urlopen(wikiurl + urlblob) as url:
                        rendered = url.read().decode()
                        pathsfound = re.search(r"id=\"output\".+?\(articlepath:(.+?)\)\(scriptpath:(.+?)?\)", rendered)
                        wikiurl = "/".join(wikiurl.split("/")[:3])
                        articlepath = pathsfound.group(1).replace("$1", "")
                        apipath = pathsfound.group(2) or ""
                        apipath = ("/" + apipath + "/api.php").replace("//", "/")
                        linksetting = {"baseurl": wikiurl, "articlepath": articlepath, "apipath": apipath}
                        if option == "wikibaselinks":
                            linksetting = {"baseurl": wikiurl, "entitypath": "/entity/", "apipath": apipath}
                    with open("group_settings.json", "r+") as f:
                        settings = json.load(f)
                        if chat_id in settings:
                            settings[chat_id][option] = linksetting
                        else:
                            settings[chat_id] = {option: linksetting}
                        f.seek(0)
                        json.dump(settings, f, indent=4)
                        f.truncate()
                    validurlentered = True
                    successtext = messages["setwiki_success"].format(options[option], wikiurl)
                    update.message.reply_html(text=successtext, disable_web_page_preview=True)
                    break
                except:
                    pass
            if not validurlentered:
                update.message.reply_html(text=messages["setwiki_invalid"], disable_web_page_preview=True)
    elif command == "/toggle" and len(message) >= 3:
        option = "toggle_" + message[1]
        options = {"toggle_normallinks": "normal [[wiki links]]", "toggle_wikibaselinks": "Wikibase entity links", "toggle_phabricator": "Phabricator links", "toggle_mylanguage": "Special:MyLanguage for [[wiki links]]", "toggle_templates": "{{template}} links"}
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
            update.message.reply_text(text=successtext, parse_mode="html")
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
    elif command == "/listconfig":
        onoff = {
            "True": "on",
            "False": "off"
        }
        configexplanations = {
            "normallinks": "Target URL for [[normal links]]: {}",
            "wikibaselinks": "Target URL for Wikibase links: {}",
            "toggle_normallinks": "Normal links are toggled {}",
            "toggle_wikibaselinks": "Wikibase links are toggled {}",
            "toggle_phabricator": "Phabricator links are toggled {}",
            "toggle_mylanguage": "Special:MyLanguage for applicable links are toggled {}",
            "toggle_templates": "Template links are toggled {}",
            "language": "The language priority list for labels is {}"
        }
        configlist = ["The following is the bot configuration for this chat. Settings in <b>bold</b> are different from the default setting.\n"]
        defaultconfig = getconfig("dummy") # Get config with a dummy chat id
        thisconfig = getconfig(update.effective_chat.id) # Get config for this chat
        for k in defaultconfig:
            if defaultconfig[k] == thisconfig[k]:
                if k in ["normallinks", "wikibaselinks"]:
                    configlist.append("· " + configexplanations[k].format(thisconfig[k]["baseurl"]) + " (<i>default</i>)")
                elif type(thisconfig[k]) is not bool:
                    configlist.append("· " + configexplanations[k].format(thisconfig[k]) + " (<i>default</i>)")
                else:
                    configlist.append("· " + configexplanations[k].format(onoff[str(thisconfig[k])]) + " (<i>default</i>)")
            else:
                if k in ["normallinks", "wikibaselinks"]:
                    configlist.append("· <b>" + configexplanations[k].format(thisconfig[k]["baseurl"]) + "</b>")
                elif type(thisconfig[k]) is not bool:
                    configlist.append("· <b>" + configexplanations[k].format(thisconfig[k]) + "</b>")
                else:
                    configlist.append("· <b>" + configexplanations[k].format(onoff[str(thisconfig[k])]) + "</b>")
        configlist.append("\nAs always, you can reply to this message with /delete to delete this message.")
        update.message.reply_text(text="\n".join(configlist), parse_mode="html", disable_web_page_preview=True)
    else:
        errortext = messages[command[1:] + "_error"]
        update.message.reply_text(text=errortext, parse_mode="html")
    with open("group_settings.json", "r") as settings:
        global global_conf
        global_conf = json.load(settings)

def delete(update, context):
    """
    Delete a message if a user asks for it.
    """
    # Check if the message is a reply, and that the message being replied
    # to is sent by this bot.
    if update.message.reply_to_message and (context.bot.username == update.message.reply_to_message.from_user.username):
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.reply_to_message.message_id)
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    else:
        update.message.reply_html(text=messages["delete_error"])

def start(update, context):
    """
    Start command that should be part of every Telegram bot.
    Also used for the /help command.
    """
    message = "start-group"
    if update.effective_chat.type == "private":
        message = "start-private"
    context.bot.send_message(chat_id=update.effective_chat.id, text=messages[message], parse_mode="html", disable_web_page_preview=True)

# Function used when testing changes to the bot with the command /echo. Uncomment to enable.
#def echo(update, context):
#    print(update.effective_chat.type)
#    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
#echo_handler = CommandHandler('echo', echo)
#updater.dispatcher.add_handler(echo_handler)

link_handler = MessageHandler(Filters.regex(regex), findlinks)
config_handler = CommandHandler(['setwiki', 'setlang', 'toggle', 'listconfig'], config)
search_handler = CommandHandler('search', search)
start_handler = CommandHandler(['start', 'help'], start)
delete_handler = CommandHandler('delete', delete)

updater.dispatcher.add_handler(link_handler)
updater.dispatcher.add_handler(config_handler)
updater.dispatcher.add_handler(search_handler)
updater.dispatcher.add_handler(start_handler)
updater.dispatcher.add_handler(delete_handler)
try:
    updater.start_polling()
    updater.idle()
except KeyboardInterrupt:
    updater.stop()
