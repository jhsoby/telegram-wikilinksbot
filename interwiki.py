# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, re

def interwiki(domain, link):
    """
    Returns direct links for interwiki links on Wikimedia wikis.
    """
    domain = domain
    if not len(link):
        return [domain, link]
    if link[0] == ":":
        link = link[1:]
    linkx = link.split(":")
    if len(linkx) == 1:
        return [domain, link]
    else:
        with urllib.request.urlopen(domain + "w/api.php?format=json&action=query&iwurl=1&titles=" + urllib.parse.quote(link)) as apiresult:
            api = json.loads(apiresult.read().decode())["query"]
            if not "interwiki" in api:
                return [domain, link]
            else:
                domain = api["interwiki"][0]["url"]
                domain = "/".join(domain.split("/")[:3]) + "/"
                link = ":".join(linkx[1:])
                return interwiki(domain, link)
                
print(interwiki("https://www.wikidata.org/", "w:no:Hallo"))