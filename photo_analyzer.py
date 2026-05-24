import aiohttp
import asyncio
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io

async def upload_to_catbox(image_bytes):
    """Resmi anonim olarak catbox.moe sunucusuna yükler ve URL döndürür."""
    url = "https://catbox.moe/user/api.php"
    
    data = aiohttp.FormData()
    data.add_field('reqtype', 'fileupload')
    data.add_field('fileToUpload', image_bytes, filename='target_photo.jpg', content_type='image/jpeg')
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=15) as response:
                if response.status == 200:
                    return await response.text()
    except Exception as e:
        print(f"Catbox yükleme hatası: {e}")
    return None

def get_exif_data(image_bytes):
    """Resimdeki EXIF ve GPS verilerini okur."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        exif_data = {}
        info = image._getexif()
        
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
                    exif_data[decoded] = gps_data
                else:
                    exif_data[decoded] = value
        return exif_data
    except Exception as e:
        print(f"EXIF okuma hatası: {e}")
        return None

def get_decimal_from_dms(dms, ref):
    """GPS koordinatlarını (Derece, Dakika, Saniye) ondalık formata çevirir (Google Haritalar için)."""
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    
    decimal = float(degrees) + float(minutes) + float(seconds)
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

def get_google_maps_url(exif_data):
    """EXIF verisinden GPS bilgilerini ayıklayıp Google Haritalar linki oluşturur."""
    if not exif_data or "GPSInfo" not in exif_data:
        return None
        
    gps_info = exif_data["GPSInfo"]
    
    # Gerekli GPS etiketlerinin olup olmadığını kontrol et
    if all(key in gps_info for key in ['GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude', 'GPSLongitudeRef']):
        lat = get_decimal_from_dms(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
        lon = get_decimal_from_dms(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])
        
        return f"https://www.google.com/maps?q={lat},{lon}"
    
    return None

def generate_search_links(image_url):
    """Yüklenen resmin URL'sini kullanarak Yandex, Google ve TinEye arama linklerini oluşturur."""
    links = {
        "Yandex (En İyi Yüz/Profil Bulucu)": f"https://yandex.com/images/search?rpt=imageview&url={image_url}",
        "Google Lens": f"https://lens.google.com/uploadbyurl?url={image_url}",
        "TinEye (Kopya Bulucu)": f"https://tineye.com/search?url={image_url}"
    }
    return links
