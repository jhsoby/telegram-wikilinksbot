# Toolforge setup

With the way this bot is currently set up on Toolforge, this is how to do updates:

1. Commit and push changes to this GitHub repo.
2. `ssh login.toolforge.org`
3. `become telegram-wikilinksbot`
4. Stop the bot with `toolforge jobs delete wikilinksbot`
5. `git pull`
6. Restart the bot with `toolforge jobs run wikilinksbot --command ./run.sh --image python3.9`

Just to restart it, in case it stops working for some reason:
* `toolforge jobs restart wikilinksbot`, or step 6 above
