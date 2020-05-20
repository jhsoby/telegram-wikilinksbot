# Telegram Wikilinksbot

This is a Python3 script that links [[wiki links]] and Wikidata entities (like [Q330574](https://www.wikidata.org/wiki/Q330574), [P31](https://www.wikidata.org/wiki/Property:P31) and [L158582](https://www.wikidata.org/wiki/Lexeme:L158582)) whenever they're used in chats.

## Features
* Links [[wiki links]] and Wikidata entities mentioned in chat messages
* Changing the default URLs used for links in one group _(group admins only)_
* Changing the language used for labels for Wikidata entities _(group admins only)_
* Toggle which type of link the bot should post _(group admins only)_

## How to use in a chat
Add **[@wikilinksbot](t.me/wikilinksbot)** to your group.

### Group configuration
The commands can only be used by group administrators or bot maintainers, in order to limit who can change its settings. The exception is if you're in a private chat with the bot, in which case anyone can set any setting.

#### Change the wiki it links to
```
/setwiki (normallinks|wikibaselinks) https://URL/
```

This command is used for changing the URL links point to. The default is [https://en.wikipedia.org/](https://en.wikipedia.org/) for [[normal links]] and [https://www.wikidata.org/](https://www.wikidata.org/) for Wikibase links. You can link other wikis like you would on-wiki using normal Wikimedia prefixes (e.g. [\[\[c:Special:UploadWizard\]\]](https://commons.wikimedia.org/wiki/Special:UploadWizard) or [\[\[de:Schadenfreude\]\]](https://de.wikipedia.org/wiki/Schadenfreude)).

URLs are assumed to follow the standar Wikimedia naming scheme where pages are found at https://URL/wiki/_page_ and the API is accessed at https://URL/w/api.php.

#### Change the language used for Wikidata labels
```
/setlang language-code
```

This command is used for changing what language Wikidata labels are fetched in. The default is `en` (English). When a different language is used, the bot will use the English label if there is no label in that other language.

For this to work, language codes must be one supported by MediaWiki (see [list in the API](https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=languages)), but the bot doesn't validate the language code except for a simple regex which checks if it could _theoretically_ be a valid languaged code.

#### Toggle link types
```
/toggle (normallinks|wikibaselinks) (on|off)
```

This command is used to turn on/off one of the link types. If both link types are turned off, the bot is essentially disabled.

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
