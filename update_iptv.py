import requests
import concurrent.futures
import time
import re

# 1. CÁC KHO CHỦ ĐỀ CHỌN LỌC
RAW_SOURCES = [
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/travel.m3u",
    "https://iptv-org.github.io/iptv/categories/education.m3u",
    "https://iptv-org.github.io/iptv/categories/lifestyle.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",
    "https://iptv-org.github.io/iptv/countries/vn.m3u"
]

def parse_m3u(url):
    print(f"📥 Đang tải và lọc danh sách từ: {url.split('/')[-1]}...")
    channels = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return []
        
        lines = response.text.splitlines()
        current_extinf = ""
        current_name = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                current_extinf = line
                parts = line.split(',')
                if len(parts) > 1: current_name = parts[-1].strip()
                    
            elif line.startswith("http"):
                if current_extinf:
                    name_lower = current_name.lower()
                    
                    # --- BỘ LỌC CHẤT LƯỢNG CAO (>= 720p) ---
                    # Quét tìm các từ khóa: 720, 1080, 2160, 4k, hd, fhd, uhd
                    if re.search(r'(720|1080|2160|4k|hd|fhd|uhd)', name_lower):
                        channels.append({
                            "extinf": current_extinf,
                            "name": current_name or "Unknown",
                            "url": line
                        })
                    current_extinf = ""
    except Exception as e:
        print(f"Lỗi tải {url}: {e}")
    return channels

def check_channel(channel):
    try:
        # Giả lập phần mềm VLC để server không chặn bot
        headers = {'User-Agent': 'VLC/3.0.16 LibVLC/3.0.16'}
        response = requests.get(channel["url"], headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            # 1. Lấy thông tin định dạng file từ server
            content_type = response.headers.get('Content-Type', '').lower()
            
            # 2. GIẾT ZOMBIE: Nếu server trả về trang web HTML (thường là trang báo lỗi fake) -> Loại ngay
            if 'text/html' in content_type:
                return None
                
            # 3. Nếu server báo đây chuẩn là luồng IPTV (m3u8)
            if 'mpegurl' in content_type or 'application/x-mpegurl' in content_type:
                # Đọc thử 1 đoạn nhỏ xem có đúng cấu trúc file stream không
                content = next(response.iter_content(chunk_size=512)).decode('utf-8', errors='ignore')
                if "#EXTM3U" in content:
                    return channel
                    
            # 4. Nếu server báo đây là file video trực tiếp (TS, MP4)
            elif 'video' in content_type or 'octet-stream' in content_type:
                return channel
                
            # 5. Trường hợp server ẩn Content-Type, bốc đại 512 bytes đầu tiên để soi cấu trúc
            else:
                content = next(response.iter_content(chunk_size=512)).decode('utf-8', errors='ignore')
                if "#EXTM3U" in content:
                    return channel
    except:
        pass
    return None

def main():
    print("🚀 BẮT ĐẦU CÀO DỮ LIỆU & LỌC KÊNH CHẤT LƯỢNG CAO...")
    start_time = time.time()
    
    all_channels = []
    for source in RAW_SOURCES:
        all_channels.extend(parse_m3u(source))
        
    unique_urls = set()
    unique_channels = []
    for ch in all_channels:
        if ch["url"] not in unique_urls:
            unique_urls.add(ch["url"])
            unique_channels.append(ch)
            
    print(f"\n✅ Đã lọc thô được {len(unique_channels)} kênh HD/FHD/4K. Bắt đầu CHẠY QUÉT SỐNG CHẾT (TIMEOUT 10S)...")
    
    valid_channels = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_channel, unique_channels)
        for res in results:
            if res:
                valid_channels.append(res)
                print(f"[VIP] {res['name']}")

    # --- EPG ĐA QUỐC GIA ---
    epg_urls = "https://iptv-org.github.io/epg/guides/uk/en.epg.xml,https://iptv-org.github.io/epg/guides/us/en.epg.xml,https://iptv-org.github.io/epg/guides/au/en.epg.xml,https://iptv-org.github.io/epg/guides/vn/vie.epg.xml"
    
    output_file = "daily_playlist.m3u"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f'#EXTM3U x-tvg-url="{epg_urls}"\n')
        
        valid_channels.sort(key=lambda x: x['name'])
        for ch in valid_channels:
            f.write(f"{ch['extinf']}\n{ch['url']}\n")
            
    print(f"\n🎯 HOÀN TẤT trong {round(time.time() - start_time, 2)} giây!")
    print(f"Tổng kết: Lọc được {len(valid_channels)} kênh VIP siêu nét và đang hoạt động.")
    print(f"File lưu tại: {output_file}")

if __name__ == "__main__":
    main()
