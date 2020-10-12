# Toolforge setup

With the way this bot is currently set up on Toolforge, this is how to do updates:

1. Commit and push changes to this GitHub repo.
2. `ssh login.toolforge.org`
3. `become telegram-wikilinksbot`
4. `script /dev/null`
5. `screen -r`
6. `screen -r <number from the list>`
7. Ctrl+C (maybe twice) to exit the current process
8. `git pull`
9. `python3 wikilinksbot.py`
10. Ctrl+A, Ctrl+D to exit screen

Just to restart it, in case it stops working for some reason:
* Steps 2–6 and 8.
