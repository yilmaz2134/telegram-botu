import asyncio
import aiohttp

# Tarama yapılacak siber istihbarat (OSINT) hedefleri
SITES = {
    "Instagram": "https://www.instagram.com/{}/",
    "TikTok": "https://www.tiktok.com/@{}",
    "X (Twitter)": "https://nitter.net/{}", 
    "GitHub": "https://github.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "Pinterest": "https://www.pinterest.com/{}/",
    "Spotify": "https://open.spotify.com/user/{}",
    "YouTube": "https://www.youtube.com/@{}",
    "Twitch": "https://www.twitch.tv/{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Medium": "https://medium.com/@{}",
    "Vimeo": "https://vimeo.com/{}",
    "SoundCloud": "https://soundcloud.com/{}",
    "Blogger": "https://{}.blogspot.com",
    "Patreon": "https://www.patreon.com/{}",
    "Linktree": "https://linktr.ee/{}",
    "Flickr": "https://www.flickr.com/people/{}",
    "DeviantArt": "https://www.deviantart.com/{}",
    "Roblox": "https://www.roblox.com/user.aspx?username={}",
    "Minecraft": "https://namemc.com/profile/{}",
    "Kick": "https://kick.com/{}",
    "Snapchat": "https://www.snapchat.com/add/{}",
    "Facebook": "https://www.facebook.com/{}",
    "VK": "https://vk.com/{}",
    "Telegram": "https://t.me/{}",
    "Behance": "https://www.behance.net/{}",
    "Dribbble": "https://dribbble.com/{}",
    "Fiverr": "https://www.fiverr.com/{}",
    "Wattpad": "https://www.wattpad.com/user/{}",
    "About.me": "https://about.me/{}",
    "BuyMeACoffee": "https://www.buymeacoffee.com/{}",
    "Kofi": "https://ko-fi.com/{}",
    "Gitea": "https://gitea.com/{}",
    "GitLab": "https://gitlab.com/{}",
    "MyAnimeList": "https://myanimelist.net/profile/{}",
    "Pastebin": "https://pastebin.com/u/{}",
    "Replit": "https://replit.com/@{}"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

async def check_site(session, site_name, url_template, username):
    url = url_template.format(username)
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as response:
            # 200 dönerse (veya 301/302 ile profile yönlendirirse) genellikle hesap var demektir.
            # Bazı siteler 404 döndürür, bazıları ise 200 dönüp sayfada "hesap bulunamadı" yazar.
            # Şimdilik en hızlı ve temel yöntem olan HTTP Kod kontrolünü kullanıyoruz.
            if response.status == 200:
                text = await response.text()
                # Yanlış pozitifleri (False Positive) engellemek için sayfa içeriklerini basitçe kontrol ediyoruz
                if "Not Found" in text or "doesn't exist" in text or "hesap bulunamadı" in text.lower():
                    return (site_name, url, False)
                return (site_name, url, True)
            else:
                return (site_name, url, False)
    except Exception:
        # Zaman aşımı veya ağ hatası olursa hesaba ulaşılamamış sayıyoruz
        return (site_name, url, False)

async def scan_username(username):
    results = []
    # aiohttp ile asenkron (çoklu) istek atıyoruz ki tarama 1 saniyede bitsin
    async with aiohttp.ClientSession() as session:
        tasks = []
        for site_name, url_template in SITES.items():
            tasks.append(check_site(session, site_name, url_template, username))
        
        # Tüm sitelere aynı anda saldırı (sorgu) yapıyoruz
        scanned_data = await asyncio.gather(*tasks)
        
        for data in scanned_data:
            if data[2] == True:
                results.append({"site": data[0], "url": data[1]})
                
    return results

if __name__ == "__main__":
    # Test amaçlı
    user = "elonmusk"
    print(f"[*] '{user}' için OSINT taraması başlatılıyor...")
    res = asyncio.run(scan_username(user))
    for r in res:
        print(f"[+] Bulundu: {r['site']} -> {r['url']}")
