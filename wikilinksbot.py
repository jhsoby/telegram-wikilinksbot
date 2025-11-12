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
regex = re.compile(r"(\[\[.+?\]\]|(?<!\{)\{\{(?!\{).+?\}\}|(?<![\w%#.\-])(?<![A-Za-z][=/])(?<!^/)(?<!Property:)(?<!Lexeme:)(?<!EntitySchema:)(?<!Item:)(?<!title=)(L[1-9]\d*(-[SF]\d+)?(@\w{2,3}(-x-Q\d+|(-\w{2,4}){0,2}))?|[QPEM][1-9]\d*(#P[1-9]\d*)?(@\w{2,3}(-\w{2,4}){0,2})?|T[1-9]\d*(#[1-9]\d*)?|Z[1-9]\d*(K[1-9]\d*)?)(@\w{2,3}(-\w{2,4}){0,2})?)")

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
			"<code>/toggle (normallinks|wikibaselinks|wikilambdalinks|phabricator|mylanguage|templates) (on|off)</code>\n\n"
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

# Language map for Wikifunctions. Wikifunctions-specific :-(
# From https://www.wikifunctions.org/wiki/Module:Wikifunctions_label by Mahir256, 2023-08-23
wflangmap = {
	"egy": "Z1049", "grc": "Z1052", "ach": "Z1054", "agq": "Z1081", "rup": "Z1097", "en-au": "Z1113", "am": "Z1184", "ady": "Z1195", "abq": "Z1196", "as": "Z1197", "cch": "Z1212", "akz": "Z1235", "ak": "Z1246", "an": "Z1269", "anp": "Z1297", "ae": "Z1300", "arw": "Z1313", "ada": "Z1317", "arq": "Z1341", "abs": "Z1349", "aro": "Z1359", "frp": "Z1378", "atj": "Z1383", "ami": "Z1398", "ab": "Z1421", "awa": "Z1422", "av": "Z1440", "sia": "Z1443", "ale": "Z1453", "ady-cyrl": "Z1475", "als": "Z1508", "rki": "Z1528", "afh": "Z1529", "af": "Z1532", "hy": "Z1541", "arc": "Z1551", "ace": "Z1562", "njo": "Z1594", "sq": "Z1608", "arp": "Z1638", "en-us": "Z1689", "akk": "Z1712", "ast": "Z1732", "ain": "Z1734", "asa": "Z1743", "ase": "Z1763", "aa": "Z1822", "de-at": "Z1843", "bss": "Z1855", "aae": "Z1879", "bci": "Z1016", "bom": "Z1017", "ksf": "Z1033", "bjn": "Z1079", "be-tarask": "Z1132", "bkh": "Z1145", "bpy": "Z1148", "en-gb": "Z1199", "ba": "Z1211", "br": "Z1282", "ban": "Z1289", "brh": "Z1293", "eu": "Z1314", "bi": "Z1315", "rml": "Z1331", "bra": "Z1366", "pt-br": "Z1381", "bik": "Z1382", "bqi": "Z1408", "brx": "Z1413", "bem": "Z1464", "bs": "Z1473", "bas": "Z1485", "bho": "Z1503", "rmn": "Z1570", "zbl": "Z1588", "bfd": "Z1595", "az": "Z1597", "bm": "Z1607", "bez": "Z1614", "be": "Z1622", "bug": "Z1623", "bew": "Z1630", "bin": "Z1662", "hbo": "Z1667", "bbc-latn": "Z1676", "byn": "Z1711", "bar": "Z1730", "bal": "Z1747", "btm": "Z1767", "bfq": "Z1773", "bax": "Z1792", "bkc": "Z1801", "bej": "Z1808", "bbc": "Z1817", "map-bms": "Z1826", "ay": "Z1865", "bzs": "Z1907", "bug-bugi": "Z1908", "bug-latn": "Z1909", "zh": "Z1006", "chn": "Z1031", "my": "Z1055", "esu": "Z1071", "dtp": "Z1088", "zh-tw": "Z1107", "qug": "Z1109", "cic": "Z1156", "bua": "Z1164", "yue": "Z1202", "rmc": "Z1215", "ch": "Z1217", "clc": "Z1225", "chp": "Z1238", "ckb": "Z1288", "shu": "Z1320", "bum": "Z1325", "car": "Z1328", "frc": "Z1334", "ce": "Z1335", "chy": "Z1348", "ccp": "Z1374", "tzm": "Z1395", "zh-mo": "Z1406", "zh-cn": "Z1411", "en-ca": "Z1437", "chb": "Z1460", "cad": "Z1461", "bcl": "Z1481", "ceb": "Z1486", "chg": "Z1496", "zh-min-nan": "Z1501", "zh-sg": "Z1504", "zh-hk": "Z1589", "zh-my": "Z1591", "cho": "Z1593", "bnn": "Z1606", "cal": "Z1621", "cay": "Z1635", "fr-ca": "Z1640", "cbk-zam": "Z1782", "ca": "Z1789", "cgg": "Z1791", "bg": "Z1823", "chr": "Z1836", "cps": "Z1857", "sro": "Z1876", "cjk": "Z1895", "yue-hans": "Z1901", "yue-hant": "Z1902", "dag": "Z1015", "dty": "Z1044", "crh": "Z1046", "da": "Z1061", "cu": "Z1105", "cr": "Z1115", "crh-latn": "Z1126", "dgr": "Z1128", "dz": "Z1147", "nl": "Z1157", "mhr": "Z1160", "ksh": "Z1182", "dv": "Z1189", "dak": "Z1190", "frs": "Z1194", "nwc": "Z1198", "ike-latn": "Z1204", "el-cy": "Z1208", "doi": "Z1209", "zh-classical": "Z1229", "swb": "Z1258", "cjm-cham": "Z1259", "cop": "Z1263", "prs": "Z1265", "hr": "Z1272", "dlc": "Z1292", "co": "Z1329", "sw-cd": "Z1358", "chk": "Z1364", "del": "Z1376", "ydd": "Z1399", "dua": "Z1442", "kw": "Z1470", "ckt": "Z1489", "syc": "Z1500", "cv": "Z1510", "crl": "Z1525", "cjm-arab": "Z1539", "cjm": "Z1572", "dyu": "Z1579", "dar": "Z1599", "bgp": "Z1659", "dzg": "Z1674", "ike-cans": "Z1702", "cjm-latn": "Z1705", "din": "Z1745", "crh-cyrl": "Z1775", "kjp": "Z1863", "ddn": "Z1890", "crh-ro": "Z1891", "en": "Z1002", "fr": "Z1004", "gez": "Z1036", "fi": "Z1051", "gay": "Z1063", "ebu": "Z1089", "et": "Z1110", "arz": "Z1114", "hif": "Z1118", "efi": "Z1119", "es-es": "Z1127", "fon": "Z1130", "gag": "Z1150", "fur": "Z1159", "gl": "Z1170", "gba": "Z1193", "fo": "Z1218", "fil": "Z1226", "de-formal": "Z1231", "ff": "Z1251", "eka": "Z1284", "pt-pt": "Z1294", "eya": "Z1310", "fat": "Z1336", "ett": "Z1368", "gan-hant": "Z1372", "gan-hans": "Z1375", "de": "Z1430", "gaa": "Z1466", "ee": "Z1509", "nl-be": "Z1517", "fj": "Z1530", "elx": "Z1537", "eo": "Z1576", "hif-latn": "Z1578", "ewo": "Z1590", "etu": "Z1660", "gur": "Z1680", "rmf": "Z1707", "myv": "Z1716", "eto": "Z1725", "egl": "Z1726", "eml": "Z1750", "ka": "Z1756", "kld": "Z1771", "lg": "Z1803", "gan": "Z1804", "fan": "Z1831", "ext": "Z1841", "fmp": "Z1847", "ha": "Z1013", "ig": "Z1014", "guw": "Z1019", "id": "Z1078", "cnh": "Z1080", "aln": "Z1084", "ht": "Z1095", "gcr": "Z1101", "is": "Z1106", "inh": "Z1122", "io": "Z1162", "nrf-gg": "Z1169", "ilo": "Z1173", "gom-latn": "Z1192", "glk": "Z1260", "hak": "Z1262", "grb": "Z1268", "bbj": "Z1283", "hmn": "Z1323", "smn": "Z1352", "gom-deva": "Z1353", "gn": "Z1357", "hup": "Z1379", "got": "Z1396", "hz": "Z1400", "guz": "Z1410", "ho": "Z1415", "haw": "Z1445", "iba": "Z1449", "hil": "Z1457", "ibb": "Z1462", "hit": "Z1487", "haz": "Z1492", "hu": "Z1513", "izh": "Z1518", "hai": "Z1651", "gon": "Z1658", "hrx": "Z1692", "gu": "Z1696", "gwi": "Z1700", "nn-hognorsk": "Z1706", "gil": "Z1759", "gor": "Z1805", "hi": "Z1820", "gom": "Z1850", "igl": "Z1852", "gpe": "Z1877", "hno": "Z1880", "bgc": "Z1886", "gcf": "Z1898", "ksw": "Z1020", "cak": "Z1027", "ia": "Z1060", "jut": "Z1068", "crb": "Z1075", "ks-arab": "Z1098", "xal": "Z1100", "bto": "Z1125", "kr": "Z1131", "cjy-hant": "Z1134", "ik": "Z1141", "ja-hira": "Z1171", "ie": "Z1185", "kac": "Z1219", "kgp": "Z1224", "jpr": "Z1277", "kbd-cyrl": "Z1290", "jam": "Z1299", "ja-hani": "Z1326", "nrf-je": "Z1337", "jv": "Z1362", "kbp": "Z1384", "krc": "Z1387", "kln": "Z1428", "ja-hrkt": "Z1444", "kbd": "Z1467", "moe": "Z1520", "krl": "Z1543", "kn": "Z1549", "kbl": "Z1557", "iu": "Z1559", "ks": "Z1561", "ks-deva": "Z1569", "kaj": "Z1573", "kaa": "Z1574", "kam": "Z1603", "jrb": "Z1619", "cjy-hans": "Z1637", "csb": "Z1665", "isu": "Z1673", "kab": "Z1687", "dyo": "Z1733", "ja-kana": "Z1736", "it": "Z1787", "kea": "Z1806", "cjy": "Z1809", "kl": "Z1813", "ja": "Z1830", "kkj": "Z1833", "ga": "Z1866", "ken": "Z1041", "sjd": "Z1042", "kiu": "Z1066", "kk-tr": "Z1070", "alc": "Z1117", "rw": "Z1123", "ker": "Z1142", "fkv": "Z1149", "kok": "Z1177", "sjk": "Z1201", "km": "Z1220", "krj": "Z1222", "kum": "Z1241", "kj": "Z1255", "kha": "Z1264", "kjh": "Z1303", "kut": "Z1305", "kg": "Z1311", "koy": "Z1347", "nmg": "Z1390", "kk-latn": "Z1418", "kv": "Z1420", "ku-arab": "Z1426", "kpe": "Z1432", "kk": "Z1441", "kk-cyrl": "Z1478", "kfo": "Z1494", "ko-kp": "Z1506", "koi": "Z1512", "kos": "Z1524", "tlh": "Z1534", "kk-kz": "Z1536", "kmb": "Z1544", "mfa": "Z1550", "ku": "Z1556", "kho": "Z1566", "kru": "Z1581", "ses": "Z1613", "ko": "Z1643", "kaw": "Z1684", "ki": "Z1693", "avk": "Z1695", "kk-arab": "Z1699", "kk-cn": "Z1731", "kri": "Z1740", "ku-latn": "Z1786", "khw": "Z1790", "bkm": "Z1795", "khq": "Z1800", "kus": "Z1883", "mde": "Z1077", "lb": "Z1099", "lou": "Z1103", "nds": "Z1146", "lzh": "Z1152", "dsb": "Z1165", "lij": "Z1175", "luo": "Z1223", "liv": "Z1228", "li": "Z1230", "quc": "Z1243", "jbo": "Z1250", "lbe": "Z1267", "lkt": "Z1271", "lah": "Z1307", "sli": "Z1309", "smj": "Z1354", "lfn": "Z1355", "lam": "Z1369", "lua": "Z1385", "ltg": "Z1388", "mk": "Z1402", "la": "Z1403", "lki": "Z1424", "lui": "Z1427", "mad": "Z1436", "lt": "Z1447", "ln": "Z1448", "lmo": "Z1452", "ky": "Z1455", "maf": "Z1468", "nds-nl": "Z1482", "lad": "Z1483", "lo": "Z1497", "lun": "Z1516", "lu": "Z1535", "es-419": "Z1547", "loz": "Z1564", "jmc": "Z1629", "luy": "Z1632", "mag": "Z1639", "lld": "Z1690", "lv": "Z1709", "lzz": "Z1715", "lez": "Z1735", "lns": "Z1779", "olo": "Z1784", "lag": "Z1828", "ldn": "Z1882", "apc": "Z1884", "ml": "Z1012", "mak": "Z1023", "mwr": "Z1029", "knn": "Z1035", "mgh": "Z1038", "mdr": "Z1047", "dum": "Z1093", "enm": "Z1111", "es-mx": "Z1133", "byv": "Z1143", "mni": "Z1151", "mcp": "Z1203", "mic": "Z1205", "mr": "Z1206", "arn": "Z1213", "gml": "Z1233", "frm": "Z1245", "mcn": "Z1253", "mga": "Z1266", "ruq": "Z1273", "mai": "Z1285", "mi": "Z1312", "mt": "Z1316", "mwv": "Z1319", "mer": "Z1377", "ms-arab": "Z1434", "chm": "Z1493", "vmf": "Z1514", "mid": "Z1526", "ms": "Z1531", "ruq-grek": "Z1542", "mrh": "Z1567", "men": "Z1568", "cdo": "Z1577", "ruq-cyrl": "Z1584", "mnc": "Z1585", "mg": "Z1625", "gv": "Z1627", "ruq-latn": "Z1634", "rwr": "Z1644", "mzn": "Z1671", "mh": "Z1703", "xmm": "Z1742", "kde": "Z1770", "gmh": "Z1794", "mas": "Z1814", "mgo": "Z1839", "man": "Z1848", "vmw": "Z1873", "acm": "Z1889", "ng": "Z1032", "ary": "Z1045", "nge": "Z1050", "lus": "Z1094", "bqz": "Z1112", "lij-mc": "Z1153", "moh": "Z1172", "ttt": "Z1188", "nan": "Z1221", "pcm": "Z1232", "ro-md": "Z1239", "nnz": "Z1248", "mus": "Z1301", "nv": "Z1306", "mfe": "Z1318", "xmf": "Z1321", "mye": "Z1454", "umu": "Z1459", "mwl": "Z1465", "nap": "Z1491", "cnr": "Z1498", "na": "Z1523", "gmy": "Z1538", "nsk": "Z1546", "new": "Z1553", "mn": "Z1554", "nia": "Z1602", "nog": "Z1604", "mnw": "Z1620", "ar-001": "Z1624", "nan-hani": "Z1647", "lol": "Z1654", "niu": "Z1661", "mo": "Z1668", "ne": "Z1675", "yrl": "Z1685", "nla": "Z1704", "nnh": "Z1713", "naq": "Z1718", "jgo": "Z1720", "mos": "Z1751", "mua": "Z1765", "mdf": "Z1766", "nl-informal": "Z1774", "sba": "Z1785", "mui": "Z1846", "ars": "Z1853", "min": "Z1860", "gld": "Z1868", "nmz": "Z1869", "no": "Z1021", "oc": "Z1059", "pro": "Z1064", "ny": "Z1074", "nxm": "Z1086", "om": "Z1087", "oj": "Z1091", "nb": "Z1227", "yas": "Z1236", "non-runr": "Z1261", "pih": "Z1274", "ojp-hira": "Z1275", "nn": "Z1276", "nod": "Z1291", "ang": "Z1333", "goh": "Z1380", "ojp": "Z1386", "ood": "Z1391", "or": "Z1419", "nqo": "Z1438", "nso": "Z1456", "ojb": "Z1477", "tog": "Z1484", "fro": "Z1499", "se": "Z1519", "peo": "Z1521", "non": "Z1560", "nov": "Z1586", "ojp-hani": "Z1601", "lrc": "Z1631", "frr": "Z1650", "lem": "Z1677", "nyo": "Z1701", "osa": "Z1727", "otk": "Z1769", "nzi": "Z1778", "nus": "Z1793", "nym": "Z1796", "os": "Z1798", "sga": "Z1802", "nah": "Z1834", "nd": "Z1835", "nyn": "Z1838", "nrm": "Z1849", "ryu": "Z1858", "nys": "Z1864", "se-fi": "Z1870", "se-no": "Z1871", "se-se": "Z1872", "ann": "Z1888", "blk": "Z1018", "pl": "Z1025", "pt": "Z1037", "pdt": "Z1057", "wes": "Z1073", "rap": "Z1090", "pwn": "Z1116", "pap": "Z1137", "fuf": "Z1178", "pon": "Z1240", "phn": "Z1244", "pau": "Z1252", "sje": "Z1278", "qya": "Z1322", "rah": "Z1324", "rgn": "Z1356", "rar": "Z1367", "rm-puter": "Z1373", "pjt": "Z1431", "pap-aw": "Z1446", "pfl": "Z1463", "ppu": "Z1490", "pag": "Z1502", "raj": "Z1558", "pam": "Z1609", "rif": "Z1617", "pi": "Z1618", "ps": "Z1641", "pnt": "Z1652", "pa": "Z1657", "phn-phnx": "Z1670", "qu": "Z1678", "pms": "Z1697", "phn-latn": "Z1721", "fa": "Z1728", "prg": "Z1741", "xpu": "Z1744", "pi-sidd": "Z1760", "pyu": "Z1781", "uun": "Z1788", "ota": "Z1825", "pcd": "Z1829", "pdc": "Z1859", "rsk": "Z1874", "en-x-piglatin": "Z1881", "cpx": "Z1903", "cpx-hant": "Z1904", "cpx-hans": "Z1905", "cpx-latn": "Z1906", "piu": "Z1910", "ru": "Z1005", "saq": "Z1022", "rof": "Z1043", "skr-arab": "Z1069", "sdc": "Z1082", "sm": "Z1144", "sam": "Z1154", "sr": "Z1158", "sr-ec": "Z1181", "xsy": "Z1214", "szy": "Z1247", "gd": "Z1339", "sc": "Z1342", "sas": "Z1345", "rom": "Z1361", "rwk": "Z1371", "sr-el": "Z1394", "rn": "Z1397", "sh": "Z1412", "rug": "Z1416", "bxr": "Z1417", "crs": "Z1425", "sel": "Z1435", "sg": "Z1469", "rm": "Z1476", "sa-sidd": "Z1479", "saz": "Z1511", "sah": "Z1533", "stq": "Z1598", "sat": "Z1600", "sad": "Z1615", "ksb": "Z1648", "rtm": "Z1649", "sh-cyrl": "Z1653", "ro": "Z1664", "sh-latn": "Z1669", "sly": "Z1688", "seh": "Z1698", "dru": "Z1710", "skr": "Z1719", "srr": "Z1722", "sa": "Z1749", "ssy": "Z1753", "sbp": "Z1754", "bat-smg": "Z1755", "rm-rumgr": "Z1768", "sei": "Z1799", "rue": "Z1815", "see": "Z1840", "sco": "Z1861", "es": "Z1003", "shy": "Z1026", "snk": "Z1028", "sw": "Z1039", "si": "Z1053", "shy-tfng": "Z1056", "sus": "Z1058", "luz": "Z1072", "en-x-simple": "Z1124", "suk": "Z1139", "sd": "Z1191", "rm-sursilv": "Z1200", "rmo": "Z1210", "sjn": "Z1295", "bcc": "Z1296", "scn": "Z1298", "szl": "Z1304", "sog": "Z1343", "sn": "Z1350", "azb": "Z1365", "ss": "Z1389", "shn": "Z1392", "st": "Z1450", "su": "Z1471", "zgh": "Z1472", "ii": "Z1480", "sk": "Z1488", "shy-arab": "Z1507", "sux": "Z1552", "rm-surmiran": "Z1571", "srn": "Z1583", "so": "Z1587", "srq": "Z1611", "sl": "Z1616", "zh-hans": "Z1645", "sms": "Z1646", "den": "Z1663", "fos": "Z1666", "sid": "Z1683", "shy-latn": "Z1691", "xog": "Z1729", "sma": "Z1738", "alt": "Z1746", "sdh": "Z1776", "bla": "Z1777", "rm-sutsilv": "Z1824", "nr": "Z1845", "dga": "Z1885", "nan-hant": "Z1892", "nan-latn": "Z1893", "to": "Z1034", "tpi": "Z1067", "syr": "Z1076", "tay": "Z1102", "ti": "Z1108", "tlb": "Z1136", "tkl": "Z1138", "tzl": "Z1163", "tnq": "Z1166", "dav": "Z1167", "teo": "Z1176", "tg": "Z1207", "tly": "Z1340", "tmh": "Z1351", "tt": "Z1401", "shi-latn": "Z1404", "gsw": "Z1405", "ter": "Z1409", "te": "Z1429", "shi-tfng": "Z1458", "de-ch": "Z1515", "bo": "Z1527", "shi": "Z1540", "tem": "Z1545", "sv": "Z1592", "ssf": "Z1596", "trv": "Z1610", "tet": "Z1612", "tiv": "Z1626", "tig": "Z1628", "roa-tara": "Z1679", "fit": "Z1681", "tli": "Z1682", "ta": "Z1694", "tt-cyrl": "Z1724", "tg-cyrl": "Z1737", "sjt": "Z1748", "fr-ch": "Z1757", "tg-latn": "Z1761", "tok": "Z1762", "tt-latn": "Z1807", "twq": "Z1811", "tl": "Z1844", "ty": "Z1856", "tdd": "Z1875", "syl": "Z1878", "tsg": "Z1887", "acq": "Z1894", "taq": "Z1896", "taq-latn": "Z1897", "vai": "Z1030", "tkr": "Z1040", "vi": "Z1048", "tn": "Z1085", "rmy": "Z1092", "sju": "Z1104", "uz": "Z1120", "ve": "Z1121", "rmg": "Z1161", "tru": "Z1168", "kcg": "Z1179", "vun": "Z1180", "uga": "Z1234", "tr": "Z1237", "tsd": "Z1254", "vot": "Z1257", "wae": "Z1270", "ug-arab": "Z1279", "tcy": "Z1281", "tum": "Z1302", "umb": "Z1308", "uk": "Z1332", "tw": "Z1344", "vec": "Z1363", "vo": "Z1370", "ug-latn": "Z1414", "tvu": "Z1433", "uz-latn": "Z1439", "udm": "Z1451", "uz-cyrl": "Z1474", "lcm": "Z1565", "aeb": "Z1582", "wls": "Z1605", "aeb-arab": "Z1633", "ts": "Z1636", "hsb": "Z1642", "rm-vallader": "Z1655", "tsi": "Z1656", "zh-hant": "Z1672", "aeb-latn": "Z1708", "ur": "Z1717", "tvl": "Z1739", "ug": "Z1752", "wa": "Z1764", "tyv": "Z1780", "bag": "Z1783", "tk": "Z1797", "vro": "Z1816", "vut": "Z1819", "vep": "Z1867", "ar": "Z1001", "cy": "Z1024", "pnb": "Z1083", "zen": "Z1096", "hsn": "Z1129", "gbz": "Z1135", "za": "Z1140", "war": "Z1155", "hu-formal": "Z1174", "mrj": "Z1183", "zza": "Z1187", "fy": "Z1216", "yao": "Z1242", "yap": "Z1249", "rmw": "Z1256", "yat": "Z1280", "sty": "Z1286", "dje": "Z1287", "cja-cham": "Z1327", "zu": "Z1330", "zea": "Z1338", "fiu-vro": "Z1346", "mul": "Z1360", "wbp": "Z1393", "diq": "Z1407", "es-formal": "Z1423", "hyw": "Z1495", "bgn": "Z1505", "cja-arab": "Z1522", "cja-latn": "Z1548", "vls": "Z1555", "wal": "Z1563", "zap": "Z1575", "tly-cyrl": "Z1580", "guc": "Z1686", "was": "Z1714", "xh": "Z1723", "zun": "Z1758", "wo": "Z1772", "ybb": "Z1810", "yi": "Z1812", "yo": "Z1818", "el": "Z1827", "abe": "Z1832", "wuu": "Z1837", "cja": "Z1842", "bdr": "Z1854", "yav": "Z1862", "wuu-hans": "Z1899", "wuu-hant": "Z1900", "bn": "Z1011", "cs": "Z1062", "pal": "Z1065", "he": "Z1186", "ban-bali": "Z1821", "th": "Z1851"
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
				if force_lang:
					force_lang = force_lang + "|"
				present_labels = data["entities"][item]["labels"] # All labels for the item
				priority_languages = (force_lang + languages + "|mul|en").split("|") # Languages for the chat, set by /setlang
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
		with urllib.request.urlopen(wb["baseurl"] + wb["apipath"] + "?action=wbgetentities&props=info&format=json&ids=" + item.split("-")[0]) as url:
			data = json.loads(url.read().decode())
			try:
				lexlang = data["entities"][item.split("-")[0]]["language"]
				lexlanglink = "<a href='" + wb["baseurl"] + wb["entitypath"] + lexlang + "'>" + labelfetcher(lexlang, languages, wb, sep_override="")[1:] + "</a>"
				if re.search(r"-F\d+", item):
					forms = data["entities"][item.split("-")[0]]["forms"]
					for form in forms:
						if form["id"] == item:
							if force_lang and force_lang in form["representations"]:
								wordform = form["representations"][force_lang]["value"]
								return sep_override + " " + wordform + " [" + lexlanglink + "]"
							else:
								labels = []
								formlangs = []
								for lang in form["representations"]:
									wordform = form["representations"][lang]["value"]
									language = form["representations"][lang]["language"]
									labels.append(wordform)
									formlangs.append(language)
								return sep_override + " " + " / ".join(labels) + " [<code>" + "/".join(formlangs) + "</code>: " + lexlanglink + "]"
				elif re.search(r"-S\d+", item):
					senses = data["entities"][item.split("-")[0]]["senses"]
					for sense in senses:
						if sense["id"] == item:
							if force_lang:
								force_lang = force_lang + "|"
							priority_languages = (force_lang + languages).split("|")
							labellang = random.choice(list(sense["glosses"].keys()))
							for lang in priority_languages[::-1]:
								if lang in list(sense["glosses"].keys()):
									labellang = lang
							label = labelfetcher(item.split("-")[0], languages, wb, sep_override="", force_lang=force_lang)[1:] + ": " + sense["glosses"][labellang]["value"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
							if not labellang == priority_languages[0]:
								label += " [<code>" + labellang + "</code>]"
							return sep_override + " " + label
				else:
					lemmas = data["entities"][item]["lemmas"]
					if force_lang and force_lang in lemmas:
						lemma = lemmas[force_lang]["value"]
						return sep_override + " " + lemma + " [" + lexlanglink + "]"
					else:
						labels = []
						lemmalangs = []
						for lang in lemmas:
							lemma = lemmas[lang]["value"]
							language = lemmas[lang]["language"]
							labels.append(lemma)
							lemmalangs.append(language)
						return sep_override + " " + " / ".join(labels) + " [<code>" + "/".join(lemmalangs) + "</code>: " + lexlanglink + "]"
			except:
				return False
	elif item[0] == "M": # Is the item a media item?
		with urllib.request.urlopen("https://commons.wikimedia.org/w/api.php?action=wbgetentities&format=json&props=info&ids=" + item) as url:
			data = json.loads(url.read().decode())
			try:
				label = data["entities"][item]["title"]
				return sep_override + " " + label
			except:
				with urllib.request.urlopen("https://commons.wikimedia.org/w/api.php?action=query&format=json&pageids=" + item[1:]) as url2:
					data2 = json.loads(url2.read().decode())
					try:
						label = data2["query"]["pages"][item[1:]]["title"]
						return sep_override + " " + label
					except:
						return False
				return False
	elif item[0] == "E": # Is the item an EntitySchema?
		# Should be replaced when EntitySchemas' terms are more
		# readily accessible via the API.
		language = languages.split("|")[0]
		if force_lang:
			language = force_lang
		with urllib.request.urlopen(wb["baseurl"] + wb["apipath"] + "?format=json&action=parse&uselang=" + language + "&page=EntitySchema:" + item) as url:
			data = json.loads(url.read().decode())
			try:
				title = data["parse"]["displaytitle"]
				label = re.search(r"<span class=\"entityschema-title-label\">([^<]+)</span>", title).group(1)
				return sep_override + " " + label
			except:
				return False
	elif item[0] == "Z": # Is the "item" a Wikilambda object?
		zid = re.findall("Z\d+", item)[0]
		if force_lang:
			languages = force_lang + "|" + languages
		viewlang = languages.split("|")[0]
		with urllib.request.urlopen("https://www.wikifunctions.org/w/api.php?format=json&action=wikilambda_fetch&formatversion=2&zids=" + zid) as url:
			data = json.loads(url.read().decode())
			try:
				data = json.loads(data[zid]["wikilambda_fetch"])
				present_labels = data["Z2K3"]["Z12K1"]
				present_labels.remove("Z11")
				labelz = random.choice(present_labels)
				labellangz = labelz["Z11K1"]
				priority_languages_pre = (languages + "|mul|en").split("|")
				priority_languages_post = []
				for lang in priority_languages_pre:
					if lang in wflangmap:
						priority_languages_post.append(wflangmap[lang])
				label_index = 1000
				for labelobj in present_labels:
					if label_index == 0:
						break
					if labelobj["Z11K1"] in priority_languages_post:
						this_index = priority_languages_post.index(labelobj["Z11K1"])
						if this_index < label_index:
							label_index = this_index
							labelz = labelobj
							labellangz = labelobj["Z11K1"]
				label = labelz["Z11K2"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
				if not labellangz == priority_languages_post[0]:
					labellang = list(wflangmap.keys())[list(wflangmap.values()).index(labellangz)]
					label += " [<code>" + labellang + "</code>]"
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
	section = ""
	if "#" in link:
		target, section = link.split("#")
		section = "#" + section
	domain = site["baseurl"]
	if not len(link):
		return [domain, link, False, False]
	if link[0] == ":":
		link = link[1:]
	linksplit = link.split(":")
	with urllib.request.urlopen(site["baseurl"] + site["apipath"] + "?format=json&action=query&iwurl=1&redirects=1&meta=userinfo&titles=" + urllib.parse.quote(link)) as apiresult:
		api = json.loads(apiresult.read().decode())["query"]
		myusername = api["userinfo"]["name"]
		if "redirects" in api:
			target = api["redirects"][0]["to"]
			if myusername in target and myusername not in link:
				target = api["redirects"][0]["from"]
			if "tofragment" in api["redirects"][0]:
				section = "#" + api["redirects"][0]["tofragment"]
			if target == link:
				return [domain, target + section, True, False]
			else:
				return [domain, link, True, target + section]
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
		elif "normalized" in api:
			target = api["normalized"][0]["to"]
			return [domain, target + section, True, False]
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
	target = urllib.parse.quote(target.replace(" ", "_"), safe="/#:")
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
	if targetsplit[0] == "int":
		target = "Special:MyLanguage/" + target
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
		if "@" in link:
			link, force_lang = link.split("@")
			result["force_lang"] = force_lang
		link, section = link.split("-")
		display = link + "-" + section
		target = link + "#" + section
	elif re.match(r"T\d+#\d+", link):
		link, section = link.split("#")
	elif "@" in link:
		link, force_lang = link.split("@")
		display = link
		target = link
		result["force_lang"] = force_lang
	linklabel = ""
	if re.match(r"L\d+-[FS]\d+", display):
		linklabel = labelfetcher(display, langconf, site, force_lang=force_lang)
	else:
		linklabel = labelfetcher(link, langconf, site, force_lang=force_lang)
	if sectionlabel:
		sectionlabel = (labelfetcher(section, langconf, site, sep_override=" →") or " → " + section)
	if section and sectionlabel:
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
	elif link[0] == "Z":
		wftarget = re.findall("Z\d+", target)[0]
		firstlang = force_lang or langconf.split("|")[0]
		result["url"] = "https://www.wikifunctions.org/view/{}/".format(firstlang) + wftarget
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
		if conf["toggle_wikibaselinks"] and re.match("^\[\[(Q|P|L|E|Property:P|Lexeme:L|EntitySchema:E)\d+\]\]$", link):
			return formatted.format(link_item(re.search("[QPLE]\d+", link)[0], conf["wikibaselinks"], conf["language"]))
		else:
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
	elif (link[0] == "Z") and conf["toggle_wikilambdalinks"]: # Is the link to a Wikifunctions object?
		linkhandler = link_item(link, conf["wikibaselinks"], conf["language"])
		if "force_lang" in linkhandler:
			return formatted_at.format(linkhandler)
		else:
			return formatted.format(linkhandler)
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
	messagetext = update.message.caption or update.message.text
	linklist = re.findall(regex, messagetext) # List all matches with the main regex
	fmt_linklist = [] # Formatted link list
	hide_preview = True
	for link in linklist:
		link = link[0].replace("\u200e", "").replace("\u200f", "") # Remove &lrm; and &rlm;, cause links to not link in some (mysterious?) circumstances
		link = linkformatter(link, getconfig(update.effective_chat.id))
		if link and (not link in fmt_linklist): # Add the formatted link to the list if it's not already there
			fmt_linklist.append(link)
	if len(fmt_linklist) == 1 and re.search("(/wiki/File:|/entity/M\d+)", fmt_linklist[0]): # TODO: Hardcoded "File" isn't nice, but better than nothing
		hide_preview = False
	if len(fmt_linklist) > 0:
		context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(fmt_linklist), disable_web_page_preview=hide_preview, disable_notification=True, parse_mode="html")

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
		"toggle_wikilambdalinks": True,
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
			validurlentered = False
			try:
				with urllib.request.urlopen(inputurl) as url:
					rendered = url.read().decode()
					find_api = re.search(r"href=\"(.+?/api.php)\?action=rsd\"", rendered).group(1)
					if find_api.startswith("//"):
						find_api = "https:" + find_api
				with urllib.request.urlopen(find_api + "?action=query&meta=siteinfo&siprop=general&format=json") as api:
					api = json.loads(api.read().decode())["query"]["general"]
					domain = api["server"]
					if domain.startswith("//"):
						domain = "https:" + domain
					articlepath = api["articlepath"].replace("$1", "")
					apipath = ("/" + api["scriptpath"] + "/api.php").replace("//", "/")
					linksetting = {"baseurl": domain, "articlepath": articlepath, "apipath": apipath}
					if option == "wikibaselinks":
						entitypath = api["wikibase-conceptbaseuri"]
						entitypath = "/" + "/".join(entitypath.split("/")[3:])
						linksetting = {"baseurl": domain, "entitypath": entitypath, "apipath": apipath}
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
				successtext = messages["setwiki_success"].format(options[option], domain)
				update.message.reply_html(text=successtext, disable_web_page_preview=True)
			except:
				pass
			if not validurlentered:
				update.message.reply_html(text=messages["setwiki_invalid"], disable_web_page_preview=True)
	elif command == "/toggle" and len(message) >= 3:
		option = "toggle_" + message[1]
		options = {"toggle_normallinks": "normal [[wiki links]]", "toggle_wikibaselinks": "Wikibase entity links", "toggle_wikilambdalinks": "Wikifunctions object links", "toggle_phabricator": "Phabricator links", "toggle_mylanguage": "Special:MyLanguage for [[wiki links]]", "toggle_templates": "{{template}} links"}
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
		languages = message[1] + "|mul|en"
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
			"toggle_wikilambdalinks": "Wikifunctions links are toggled {}",
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
		configlist.append("\nAs always, you can reply to this message with /delete to delete it.")
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
#	print(update.effective_chat.type)
#	context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
#echo_handler = CommandHandler('echo', echo)
#updater.dispatcher.add_handler(echo_handler)

link_handler = MessageHandler(Filters.regex(regex), findlinks)
media_link_handler = MessageHandler(Filters.caption_regex(regex), findlinks)
config_handler = CommandHandler(['setwiki', 'setlang', 'toggle', 'listconfig'], config)
search_handler = CommandHandler('search', search)
start_handler = CommandHandler(['start', 'help'], start)
delete_handler = CommandHandler('delete', delete)

updater.dispatcher.add_handler(link_handler)
updater.dispatcher.add_handler(media_link_handler)
updater.dispatcher.add_handler(config_handler)
updater.dispatcher.add_handler(search_handler)
updater.dispatcher.add_handler(start_handler)
updater.dispatcher.add_handler(delete_handler)
try:
	updater.start_polling()
	updater.idle()
except KeyboardInterrupt:
	updater.stop()
