# Telegram Wikilinksbot

This is a Python3 script that links [[wiki links]], Wikidata entities (like [Q330574](https://www.wikidata.org/wiki/Q330574), [P31](https://www.wikidata.org/wiki/Property:P31) and [L158582](https://www.wikidata.org/wiki/Lexeme:L158582)), Wikimedia Commons media entities (like [M1905684](https://commons.wikimedia.org/entity/M1905684)), Wikifunctions objects (like [Z10123](https://www.wikifunctions.org/view/en/Z10123)), and Wikimedia Phabricator tasks (like [T39625](https://phabricator.wikimedia.org/T39625)) whenever they're used in chats.

## Features
* Links [[wiki links]] and {{templates}} mentioned in chat messages
  * Links to redirects link directly to the target pages and show their titles
  * Interwiki links link directly to the correct target sites
* Links Wikidata (or other Wikibase) entities mentioned in chat messages
  * You can also link specific properties in an entity, or to specific
  lexeme forms or senses
* Links Wikimedia Commons media entities mentioned in chat messages
* Links Wikifunctions objects mentioned in chat messages
* Links Phabricator tasks mentioned in chat messages
* The bot can delete its own messages when they are replied to with `/delete`
  * It will also try to delete the message with the `/delete` command, but this
  only works if the bot has the right to delete messages (is group admin)
* Search the group's wiki with `/search search query`. Default is the first 3
  results; optionally return a different amount of results with `/search:x
  search query` where `x` is any number between 1 and 10.
* Can link practically any publically available wiki.
* Changing the default URLs used for links in one group _(group admins only)_
* Changing the language used for labels for Wikidata entities _(group admins only)_
* Toggle which type of link the bot should post _(group admins only)_
* List the current configuration of the bot _(group admins only)_

## How to use in a chat
Add **[@wikilinksbot](https://t.me/wikilinksbot)** to your group, and test it out by sending
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

This command is used for changing the URL links point to. The default is [https://en.wikipedia.org/](https://en.wikipedia.org/) for [[normal links]] and [https://www.wikidata.org/](https://www.wikidata.org/) for Wikibase links. You can link other wikis like you would on-wiki using interwiki prefixes (e.g. [\[\[c:Special:UploadWizard\]\]](https://commons.wikimedia.org/wiki/Special:UploadWizard) or [\[\[de:Schadenfreude\]\]](https://de.wikipedia.org/wiki/Schadenfreude)).

Practically any publically available MediaWiki wiki can be set as the target wiki. If the wiki follows an unusual URL scheme (i.e. something other than `$URL/wiki/Pagename`), try using the URL of a page on the wiki when setting this option.

**Examples:**  
Set [[normal links]] to link to the Shawiya Wiktionary:
```
/setwiki normallinks https://shy.wiktionary.org
```
Set [[normal links]] to link to the Minecraft Gamepedia:
```
/setwiki normallinks https://minecraft.gamepedia.com
```
Set Wikibase links to link to the Open Street Map wiki:
```
/setwiki wikibaselinks https://wiki.openstreetmap.org/
```

#### Change the language priority used for Wikibase labels
```
/setlang language-code
/setlang language-code-1|language-code-2|language-code-3
```

This command is used for changing what language Wikidata labels are fetched in. You can set a number of languages in prioritized order, separated with the pipe character (`|`). English (`en`) is always the last fallback, but it can also be specified before other languages.

If an item doesn't have a label in any of the priority languages (or English), the bot will pick a label at random. If you want show the label in a specific language as a one-off, you can use the syntax `Q1234@langcode`, e.g. `Q20@se` will show "Q20 – Norga" no matter what language priority is set for the chat.

For this to work, the language code(s) must be supported by MediaWiki (see [list in the API](https://www.wikidata.org/w/api.php?action=query&meta=siteinfo&siprop=languages)), but the bot doesn't validate the language code except for a simple regex which checks if it could _theoretically_ be a valid language code.

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
/toggle (normallinks|wikibaselinks|wikilambdalinks|phabricator|mylanguage|templates) (on|off)
```

This command is used to turn one of the link types on or off. If all link types are turned off, the bot is essentially disabled. By default, all are turned on.

`mylanguage` toggles whether or not links should be prefixed with "Special:MyLanguage/". When toggled on, this will only happen for links to translatable pages.

**Example:**  
Disable Wikibase links:
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
