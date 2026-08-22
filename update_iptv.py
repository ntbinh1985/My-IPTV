import requests
import concurrent.futures
import time

# --- THÊM KHO QUỐC GIA ĐỂ SĂN SKY, TNT, ASTRO ---
RAW_SOURCES = [
    "https://iptv-org.github.io/iptv/categories/sports.m3u", # Tổng kho Thể thao
    "https://iptv-org.github.io/iptv/countries/uk.m3u",      # Kho UK (Săn Sky, TNT)
    "https://iptv-org.github.io/iptv/countries/my.m3u",      # Kho Malaysia (Săn Astro)
    "https://iptv-org.github.io/iptv/categories/movies.m3u", # Tổng kho Phim
    "https://iptv-org.github.io/iptv/countries/vn.m3u"       # Kho Việt Nam
]

def parse_m3u_from_url(url):
    print(f"Đang lấy dữ liệu từ: {url.split('/')[-1]}...")
    channels = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return []
        
        lines = response.text.splitlines()
        current_extinf, current_name, current_group = "", "", "Khác"
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                current_extinf = line
                parts = line.split(',')
                if len(parts) > 1: current_name = parts[-1].strip()
                if 'group-title="' in line:
                    current_group = line.split('group-title="')[1].split('"')[0]
            elif line.startswith("http"):
                if current_extinf:
                    # Tự động gán nhóm "Thể thao" nếu tên kênh chứa từ khóa thể thao
                    name_lower = current_name.lower()
                    if any(kw in name_lower for kw in ['sky sport', 'tnt', 'astro', 'espn', 'bein']):
                        current_group = "Sports (VIP)"
                        
                    channels.append({
                        "extinf": current_extinf, "name": current_name or "Unknown",
                        "group": current_group, "url": line
                    })
                    current_extinf, current_name, current_group = "", "", "Khác"
        return channels
    except: return []

def check_channel(channel):
    try:
        headers = {'User-Agent': 'VLC/3.0.16'}
        response = requests.get(channel["url"], headers=headers, timeout=5, stream=True)
        if response.status_code == 200:
            content = next(response.iter_content(chunk_size=1024)).decode('utf-8', errors='ignore')
            if "#EXTM3U" in content or "#EXTINF" in content or "http" in content:
                return channel
    except: pass
    return None

def main():
    print("Bắt đầu gom kênh từ các kho...")
    all_channels = []
    for source in RAW_SOURCES:
        all_channels.extend(parse_m3u_from_url(source))
        
    unique_urls = set()
    unique_channels = []
    for ch in all_channels:
        if ch["url"] not in unique_urls:
            unique_urls.add(ch["url"])
            unique_channels.append(ch)
            
    print(f"Tổng cộng có {len(unique_channels)} kênh độc nhất. Bắt đầu quét SÂU (sẽ mất vài phút)...")
    
    # ĐÃ GỠ BỎ GIỚI HẠN, QUÉT TOÀN BỘ KÊNH
    valid_channels = []
    
    # Tăng max_workers lên 100 để GitHub cày nhanh hơn
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        results = executor.map(check_channel, unique_channels)
        for res in results:
            if res: 
                valid_channels.append(res)
                print(f"[LIVE] {res['name']}")

    # Xuất file kèm EPG
    output_filename = "daily_playlist.m3u"
    epg_url = "https://iptv-org.github.io/epg/guides/vn/vie.epg.xml"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
        valid_channels.sort(key=lambda x: x['group'])
        for ch in valid_channels:
            f.write(f"{ch['extinf']}\n{ch['url']}\n")
            
    print(f"Hoàn tất! Cứu sống được {len(valid_channels)} kênh.")

if __name__ == "__main__":
    main()
