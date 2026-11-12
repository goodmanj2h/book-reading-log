import urllib.request
import urllib.parse
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

query = urllib.parse.quote("The System")
url = f"https://www.yes24.com/Product/Search?domain=ALL&query={query}"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
    print("Fetched Yes24 search results.")
    
    img = re.search(r'<img[^>]+class="lazy"[^>]+data-original="([^"]+)"', html)
    author = re.search(r'<span class="authPub info_auth">.*?<a[^>]+>([^<]+)</a>', html, re.DOTALL)
    pub = re.search(r'<span class="authPub info_pub">.*?<a[^>]+>([^<]+)</a>', html, re.DOTALL)
    
    print("IMG:", img.group(1) if img else "Not found")
    print("AUTHOR:", author.group(1).strip() if author else "Not found")
    print("PUB:", pub.group(1).strip() if pub else "Not found")
    
except Exception as e:
    print("Error:", e)
