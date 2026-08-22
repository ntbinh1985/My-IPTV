import requests
import concurrent.futures
import time

RAW_SOURCES = [
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/countries/vn.m3u"
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
    all_channels = []
    for source in RAW_SOURCES:
        all_channels.extend(parse_m3u_from_url(source))
        
    unique_urls = set()
    unique_channels = []
    for ch in all_channels:
        if ch["url"] not in unique_urls:
            unique_urls.add(ch["url"])
            unique_channels.append(ch)
            
    # Giới hạn 50 kênh để test nhanh trên GitHub Actions. Xóa [:50] để quét toàn bộ.
    channels_to_test = unique_channels[:50] 
    valid_channels = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_channel, channels_to_test)
        for res in results:
            if res: valid_channels.append(res)

    # Xuất file kèm EPG
    output_filename = "daily_playlist.m3u"
    epg_url = "https://iptv-org.github.io/epg/guides/vn/vie.epg.xml"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
        valid_channels.sort(key=lambda x: x['group'])
        for ch in valid_channels:
            f.write(f"{ch['extinf']}\n{ch['url']}\n")

if __name__ == "__main__":
    main()