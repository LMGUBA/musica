import random
import time
from flask import Flask, request, render_template, jsonify
import yt_dlp
import ssl
import json
from urllib.parse import quote
import concurrent.futures
import threading
from functools import lru_cache
import requests

app = Flask(__name__)

# Deshabilitar verificación SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

# Sistema anti-detección mejorado
class YouTubeStealthSystem:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        self.proxy_list = [
            # Agrega aquí proxies si los tienes
            # 'http://proxy1:port',
            # 'http://proxy2:port',
        ]
        
        self.request_delay_range = (0.5, 2.0)  # Delay aleatorio entre requests
        self.last_request_time = 0
        
    def get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def get_random_proxy(self):
        if self.proxy_list:
            return random.choice(self.proxy_list)
        return None
    
    def apply_request_delay(self):
        """Aplicar delay aleatorio entre requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        min_delay = self.request_delay_range[0]
        if time_since_last < min_delay:
            delay = random.uniform(min_delay, self.request_delay_range[1])
            time.sleep(delay)
        
        self.last_request_time = time.time()
    
    def get_stealth_headers(self):
        """Generar headers que simulan un navegador real"""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
    
    def get_ydl_opts_stealth(self, format_selector='bestaudio'):
        """Configuración yt-dlp con máximo sigilo"""
        proxy = self.get_random_proxy()
        
        opts = {
            'format': format_selector,
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'prefer_insecure': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'http_headers': self.get_stealth_headers(),
            'extract_flat': True,
            'ignoreerrors': True,
            # Configuraciones anti-detección adicionales
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'age_limit': 999,
            'sleep_interval': random.uniform(0.5, 1.5),
            'max_sleep_interval': 3,
            'retries': 3,
            'fragment_retries': 3,
            'file_access_retries': 3,
        }
        
        if proxy:
            opts['proxy'] = proxy
            
        return opts

# Instancia del sistema stealth
stealth_system = YouTubeStealthSystem()

# Cache para resultados de búsqueda recientes
search_cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 300  # 5 minutos

# Simulador de actividad de Spotify (señuelo)
class SpotifyDecoy:
    def __init__(self):
        self.spotify_endpoints = [
            'https://api.spotify.com/v1/search',
            'https://api.spotify.com/v1/tracks',
            'https://api.spotify.com/v1/playlists'
        ]
    
    def make_decoy_request(self):
        """Hacer request falso a Spotify para confundir tracking"""
        try:
            endpoint = random.choice(self.spotify_endpoints)
            headers = stealth_system.get_stealth_headers()
            
            # Request que fallará pero generará tráfico legítimo
            requests.get(endpoint, headers=headers, timeout=5)
        except:
            pass  # Ignorar errores, es solo un señuelo

spotify_decoy = SpotifyDecoy()

@app.route("/", methods=["GET", "POST"])
def index():
    # Hacer request señuelo ocasionalmente
    if random.random() < 0.3:  # 30% de probabilidad
        threading.Thread(target=spotify_decoy.make_decoy_request, daemon=True).start()
    
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            return render_template("index.html", 
                                 error="Por favor ingresa un término de búsqueda")
        
        try:
            # Aplicar delay anti-detección
            stealth_system.apply_request_delay()
            
            # Buscar canciones con sigilo
            search_results = search_songs_stealth(query)
            if search_results:
                return render_template("index.html", 
                                     search_results=search_results,
                                     query=query)
            else:
                return render_template("index.html", 
                                     error="No se encontraron resultados")
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            return render_template("index.html", 
                                 error="Error al buscar canciones")

    return render_template("index.html")

@app.route("/get_audio_url", methods=["POST"])
def get_audio_url():
    """Obtener URL de audio directo con máximo sigilo"""
    try:
        # Request señuelo
        if random.random() < 0.5:
            threading.Thread(target=spotify_decoy.make_decoy_request, daemon=True).start()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "URL no proporcionada"}), 400
        
        # Aplicar delay anti-detección
        stealth_system.apply_request_delay()
        
        print(f"Obteniendo audio con sigilo para: {video_url}")
        audio_url = get_direct_audio_url_stealth(video_url)
        
        if audio_url:
            print(f"URL de audio obtenida exitosamente con sigilo")
            return jsonify({"success": True, "audio_url": audio_url})
        else:
            print("No se pudo obtener URL de audio")
            return jsonify({"error": "No se pudo obtener URL de audio válida"}), 500
            
    except Exception as e:
        print(f"Error al obtener audio: {e}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

def search_songs_stealth(search_term, max_results=15):
    """Búsqueda con máximo sigilo y anti-detección"""
    
    # Verificar cache primero
    cached_results = get_from_cache(search_term)
    if cached_results:
        return cached_results
    
    print(f"Búsqueda sigilosa para: {search_term}")
    start_time = time.time()
    
    search_variations = generate_search_variations_optimized(search_term)
    all_results = []
    
    # Búsquedas secuenciales con delays para evitar detección
    for variation in search_variations:
        try:
            # Aplicar delay entre variaciones
            stealth_system.apply_request_delay()
            
            # Request señuelo ocasional
            if random.random() < 0.4:
                threading.Thread(target=spotify_decoy.make_decoy_request, daemon=True).start()
            
            results = search_single_variation_stealth(variation, max_results // len(search_variations) + 3)
            all_results.extend(results)
            
            print(f"Completada búsqueda sigilosa para: {variation} ({len(results)} resultados)")
            
        except Exception as e:
            print(f"Error en búsqueda sigilosa para '{variation}': {e}")
    
    # Eliminar duplicados
    unique_results = []
    seen_ids = set()
    
    for result in all_results:
        result_id = result.get('id') or result.get('url', '')
        if result_id and result_id not in seen_ids:
            seen_ids.add(result_id)
            unique_results.append(result)
            
            if len(unique_results) >= max_results:
                break
    
    # Guardar en cache
    save_to_cache(search_term, unique_results)
    
    elapsed_time = time.time() - start_time
    print(f"Búsqueda sigilosa completada en {elapsed_time:.2f} segundos - {len(unique_results)} resultados")
    
    return unique_results

def search_single_variation_stealth(variation, results_per_variation=10):
    """Buscar una sola variación con sigilo máximo"""
    search_query = f"ytsearch{results_per_variation}:{variation}"
    
    ydl_opts = stealth_system.get_ydl_opts_stealth()
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            results = []
            if 'entries' in info and info['entries']:
                for entry in info['entries'][:results_per_variation]:
                    if entry and entry.get('title') and entry.get('url'):
                        result_data = {
                            'title': clean_string(entry.get('title', 'Título desconocido')),
                            'uploader': clean_string(entry.get('uploader', entry.get('channel', 'Canal desconocido'))),
                            'duration': format_duration(entry.get('duration', 0)),
                            'view_count': format_views(entry.get('view_count', 0)),
                            'url': entry.get('url', ''),
                            'thumbnail': get_best_thumbnail(entry.get('thumbnails', [])),
                            'id': entry.get('id', ''),
                            'upload_date': entry.get('upload_date', '')
                        }
                        results.append(result_data)
            
            return results
            
    except Exception as e:
        print(f"Error en variación sigilosa '{variation}': {str(e)}")
        return []

@lru_cache(maxsize=50)
def get_direct_audio_url_stealth(video_url):
    """Obtener URL directo del audio con máximo sigilo"""
    ydl_opts = stealth_system.get_ydl_opts_stealth('bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info or not info.get('formats'):
                return None
            
            formats = info.get('formats', [])
            
            for fmt in formats:
                if (fmt.get('acodec') and fmt.get('acodec') != 'none' and 
                    fmt.get('url') and
                    fmt.get('ext') in ['webm', 'm4a', 'mp4'] and
                    not fmt.get('url').startswith('https://manifest')):
                    
                    return fmt.get('url')
            
            return None
            
    except Exception as e:
        print(f"Error obteniendo URL de audio con sigilo: {e}")
        return None

# Funciones auxiliares (mantenidas del código original)
def get_cache_key(search_term):
    return search_term.lower().strip()

def get_from_cache(search_term):
    cache_key = get_cache_key(search_term)
    with cache_lock:
        if cache_key in search_cache:
            cached_data, timestamp = search_cache[cache_key]
            if time.time() - timestamp < CACHE_EXPIRY:
                print(f"Resultados obtenidos del cache para: {search_term}")
                return cached_data
            else:
                del search_cache[cache_key]
    return None

def save_to_cache(search_term, results):
    cache_key = get_cache_key(search_term)
    with cache_lock:
        search_cache[cache_key] = (results, time.time())
        if len(search_cache) > 100:
            oldest_key = min(search_cache.keys(), 
                           key=lambda k: search_cache[k][1])
            del search_cache[oldest_key]

def generate_search_variations_optimized(search_term):
    variations = [search_term]
    
    if len(search_term) > 3:
        variations.append(f"{search_term} oficial")
        
        search_lower = search_term.lower()
        known_artists = {
            'kudai': 'kudai sin despertar',
            'mana': 'mana banda',
            'chayanne': 'chayanne bailando',
            'shakira': 'shakira waka',
            'mago de oz': 'mago de oz fiesta'
        }
        
        for artist, variation in known_artists.items():
            if artist in search_lower:
                variations.append(variation)
                break
    
    return variations[:3]

def get_best_thumbnail(thumbnails):
    if not thumbnails:
        return ""
    
    for thumb in thumbnails:
        if thumb.get('url') and 'mqdefault' in thumb.get('url', ''):
            return thumb['url']
    
    for thumb in thumbnails:
        if thumb.get('url'):
            return thumb['url']
    
    return ""

def format_duration(duration):
    if not duration or duration == 0:
        return "Desconocido"
    
    try:
        duration = int(duration)
        return f"{duration//60}:{duration%60:02d}"
    except (ValueError, TypeError):
        return "Desconocido"

def clean_string(text):
    if not text:
        return ""
    return str(text).replace("'", "&#39;").replace('"', "&quot;")

def format_views(views):
    if not views:
        return "0"
    
    try:
        views = int(views)
        if views >= 1000000:
            return f"{views/1000000:.1f}M"
        elif views >= 1000:
            return f"{views/1000:.1f}K"
        else:
            return str(views)
    except (ValueError, TypeError):
        return "0"

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Error interno del servidor"), 500

if __name__ == "__main__":
    print("Iniciando servidor Flask con sistema anti-detección...")
    print("Accede a: http://localhost:8080")
    print("Características de sigilo activadas:")
    print("- Rotación de User-Agents")
    print("- Delays aleatorios entre requests")
    print("- Headers de navegador real")
    print("- Requests señuelo a Spotify")
    print("- Geo-bypass activado")
    print("- Cache de búsquedas (5 min)")
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)