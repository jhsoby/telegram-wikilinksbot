# Telegram Wikilinksbot

This is a Python3 script that links [[wiki links]], Wikidata entities (like [Q330574](https://www.wikidata.org/wiki/Q330574), [P31](https://www.wikidata.org/wiki/Property:P31) and [L158582](https://www.wikidata.org/wiki/Lexeme:L158582)) or Wikimedia Phabricator tasks (like [T39625](https://phabricator.wikimedia.org/T39625))whenever they're used in chats.

## Features
* Links [[wiki links]] mentioned in chat messages
* Links Wikidata entities mentioned in chat messages
* Links Phabricator tasks mentioned in chat messages (off by default)
* Can delete its own messages when they are replied to with `/delete`
* Changing the default URLs used for links in one group _(group admins only)_
* Changing the language used for labels for Wikidata entities _(group admins only)_
* Toggle which type of link the bot should post _(group admins only)_
* List the current configuration of the bot _(group admins only)_

## How to use in a chat
Add **[@wikilinksbot](t.me/wikilinksbot)** to your group, and test it out by sending
a message with a [[wiki link]] or a Wikidata entity like Q42.

If you don't like one of the messages the bot has sent, you can reply to it with `/delete`,
and the bot will delete that message. It will also attempt to delete your /delete message,
but that will only work if the bot is a group admin or you are in a private chat with
the bot. If that's not the case, you will have to delete that message manually yourself.

### Group configuration
The commands can only be used by group administrators or bot maintainers, in order to limit who can change its settings. The exception is if you're in a private chat with the bot, in which case anyone can set any setting.

#### Change the wiki it links to
```
/setwiki (normallinks|wikibaselinks) https://URL/
```

This command is used for changing the URL links point to. The default is [https://en.wikipedia.org/](https://en.wikipedia.org/) for [[normal links]] and [https://www.wikidata.org/](https://www.wikidata.org/) for Wikibase links. You can link other wikis like you would on-wiki using normal Wikimedia prefixes (e.g. [\[\[c:Special:UploadWizard\]\]](https://commons.wikimedia.org/wiki/Special:UploadWizard) or [\[\[de:Schadenfreude\]\]](https://de.wikipedia.org/wiki/Schadenfreude)).

URLs are assumed to follow the standard Wikimedia naming scheme where pages are found at https://URL/wiki/_page_ and the API is accessed at https://URL/w/api.php.

**Example:**  
Set [[normal links]] to link to the Shawiya Wiktionary.
```
/setwiki normallinks https://shy.wiktionary.org/
```

#### Change the language used for Wikidata labels
```
/setlang language-code
/setlang language-code-1|language-code-2|language-code-3
```

This command is used for changing what language Wikidata labels are fetched in. You can set a number of languages in prioritized order, separated with the pipe character (`|`). English (`en`) is always the last fallback, but it can also be specified before other languages.

For this to work, the language code(s) must be supported by MediaWiki (see [list in the API](https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=languages)), but the bot doesn't validate the language code except for a simple regex which checks if it could _theoretically_ be a valid languaged code.

**Examples:**  
Set the label language to Persian:
```
/setlang fa
```
Set the label language order to Norwegian Bokmål, Norwegian Nynorsk, Swedish and Danish:
```
/setlang nb|nn|sv|da
```

#### Toggle link types
```
/toggle (normallinks|wikibaselinks|phabricator) (on|off)
```

This command is used to turn on/off one of the link types. If all link types are turned off, the bot is essentially disabled. By default, normal links and Wikibase links are turned on, while Phabricator links are turned off.

**Example:**  
Disable Wikidata links:
```
/toggle wikibaselinks off
```

#### List bot configuration
```
/listconfig
```

This command will make the bot list the configuration for the current chat, highlighting options that are different from the default.

## How to run
### Prerequisites
You need the Python module [`python-telegram-bot`](https://python-telegram-bot.org/). You can install it with:

```
pip3 install python-telegram-bot
```

You will also need to create a Telegram bot account via [@BotFather](https://t.me./botfather), just follow the instructions in the chat. The bot needs privacy mode disabled in order to read messages in chats. This is changed in BotFather.

You also need your numeric Telegram user id, which you can get via the python-telegram-bot module, or simply by sending `/start` to [@userinfobot](https://t.me./userinfobot).

### Run
```
python3 wikilinksbot.py
```

And that's it!
