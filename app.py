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
import base64

app = Flask(__name__)

# Deshabilitar verificación SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

# Configuración de credenciales de Spotify
SPOTIFY_CONFIG = {
    'client_id': 'c508ae6a444f4d16877ba4dcecbba1ab',
    'client_secret': '66c896d517ec497dad0d59f00fed258c'
}

# Sistema anti-detección mejorado con Spotify integrado
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

# Sistema de autenticación y actividad de Spotify (mejorado)
class SpotifyAntiDetection:
    def __init__(self):
        self.client_id = SPOTIFY_CONFIG['client_id']
        self.client_secret = SPOTIFY_CONFIG['client_secret']
        self.access_token = None
        self.token_expires_at = 0
        self.search_terms_used = []
        
        # Géneros y artistas populares para búsquedas realistas
        self.popular_searches = [
            "reggaeton 2024", "bad bunny", "taylor swift", "pop latino",
            "rock en español", "salsa", "bachata", "merengue", "cumbia",
            "indie rock", "electronic", "hip hop", "r&b", "jazz",
            "classical", "country", "folk", "blues", "reggae",
            "metal", "punk", "alternative", "house", "techno"
        ]
        
        # Playlists populares para simular actividad real
        self.popular_playlists = [
            "Today's Top Hits", "RapCaviar", "Hot Country", "Rock This",
            "Viva Latino", "Peaceful Piano", "Deep Focus", "Chill Hits",
            "Pop Rising", "Indie Pop", "Electronic Focus", "Jazz Vibes"
        ]
    
    def get_access_token(self):
        """Obtener token de acceso real de Spotify"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            # Codificar credenciales
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'grant_type': 'client_credentials'}
            
            response = requests.post(
                'https://accounts.spotify.com/api/token',
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                # Token expira en 1 hora, renovamos 5 min antes
                self.token_expires_at = time.time() + token_data['expires_in'] - 300
                print("✓ Token de Spotify obtenido exitosamente")
                return self.access_token
            else:
                print(f"✗ Error obteniendo token de Spotify: {response.status_code}")
                return None
        except Exception as e:
            print(f"✗ Error de autenticación Spotify: {e}")
            return None
    
    def make_realistic_spotify_search(self, original_query=None):
        """Hacer búsqueda real en Spotify para generar tráfico legítimo"""
        token = self.get_access_token()
        if not token:
            return False
        
        try:
            # Elegir término de búsqueda realista
            if original_query and random.random() < 0.3:  # 30% usar query original
                search_term = original_query
            else:
                search_term = random.choice(self.popular_searches)
            
            # Evitar repetir búsquedas muy seguido
            if search_term in self.search_terms_used[-5:]:
                search_term = random.choice(self.popular_searches)
            
            self.search_terms_used.append(search_term)
            if len(self.search_terms_used) > 20:
                self.search_terms_used.pop(0)
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                **stealth_system.get_stealth_headers()
            }
            
            # Búsqueda real en Spotify
            search_url = 'https://api.spotify.com/v1/search'
            params = {
                'q': search_term,
                'type': 'track,artist,album',
                'limit': random.randint(10, 50),
                'market': 'US'
            }
            
            response = requests.get(
                search_url,
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks_found = len(data.get('tracks', {}).get('items', []))
                print(f"✓ Búsqueda Spotify exitosa: '{search_term}' ({tracks_found} tracks)")
                return True
            else:
                print(f"✗ Error en búsqueda Spotify: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error en búsqueda Spotify: {e}")
            return False
    
    def get_playlist_tracks(self):
        """Obtener tracks de playlist popular para simular navegación"""
        token = self.get_access_token()
        if not token:
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {token}',
                **stealth_system.get_stealth_headers()
            }
            
            # Buscar playlist por nombre
            playlist_name = random.choice(self.popular_playlists)
            search_url = 'https://api.spotify.com/v1/search'
            params = {
                'q': playlist_name,
                'type': 'playlist',
                'limit': 1
            }
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                playlists = response.json().get('playlists', {}).get('items', [])
                if playlists:
                    playlist_id = playlists[0]['id']
                    
                    # Obtener tracks de la playlist
                    tracks_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
                    tracks_response = requests.get(tracks_url, headers=headers, timeout=10)
                    
                    if tracks_response.status_code == 200:
                        print(f"✓ Playlist Spotify accedida: '{playlist_name}'")
                        return True
            
            return False
        except Exception as e:
            print(f"✗ Error accediendo playlist: {e}")
            return False
    
    def simulate_user_behavior(self, original_query=None):
        """Simular comportamiento real de usuario de Spotify"""
        actions = [
            ('search', 0.6),  # 60% probabilidad de búsqueda
            ('playlist', 0.3),  # 30% probabilidad de playlist
            ('wait', 0.1)  # 10% probabilidad de solo esperar
        ]
        
        # Seleccionar acción basada en probabilidades
        rand = random.random()
        cumulative_prob = 0
        
        for action, prob in actions:
            cumulative_prob += prob
            if rand <= cumulative_prob:
                if action == 'search':
                    return self.make_realistic_spotify_search(original_query)
                elif action == 'playlist':
                    return self.get_playlist_tracks()
                else:  # wait
                    time.sleep(random.uniform(1, 3))
                    return True
        
        return False

# Instancia del sistema anti-detección Spotify
spotify_system = SpotifyAntiDetection()

@app.route("/", methods=["GET", "POST"])
def index():
    # Actividad Spotify realista en background
    if random.random() < 0.4:  # 40% de probabilidad
        threading.Thread(
            target=spotify_system.simulate_user_behavior,
            daemon=True
        ).start()
    
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            return render_template("index.html", 
                                 error="Por favor ingresa un término de búsqueda")
        
        try:
            # Aplicar delay anti-detección
            stealth_system.apply_request_delay()
            
            # Actividad Spotify con query original
            threading.Thread(
                target=spotify_system.simulate_user_behavior,
                args=(query,),
                daemon=True
            ).start()
            
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
    """Obtener URL de audio directo con máximo sigilo y múltiples respaldos"""
    start_time = time.time()
    
    try:
        # Actividad Spotify intensiva durante descarga
        if random.random() < 0.8:  # 80% probabilidad
            threading.Thread(
                target=spotify_system.simulate_user_behavior,
                daemon=True
            ).start()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "URL no proporcionada"}), 400
        
        print(f"🎯 Iniciando extracción de audio para: {video_url}")
        
        # Aplicar delay anti-detección inicial
        stealth_system.apply_request_delay()
        
        # Actividad Spotify paralela intensiva
        for _ in range(2):  # Múltiples threads de Spotify
            threading.Thread(
                target=spotify_system.simulate_user_behavior,
                daemon=True
            ).start()
        
        # Intentar extracción con múltiples métodos
        audio_url = None
        
        # Método 1: Extracción estándar mejorada
        print("🔄 Método 1: Extracción estándar...")
        audio_url = get_direct_audio_url_stealth(video_url)
        
        # Método 2: Extracción de respaldo si falló el primero
        if not audio_url:
            print("🔄 Método 2: Extracción alternativa...")
            time.sleep(random.uniform(1, 3))
            
            # Más actividad Spotify
            threading.Thread(
                target=spotify_system.make_realistic_spotify_search,
                daemon=True
            ).start()
            
            audio_url = get_fallback_audio_url(video_url)
        
        # Método 3: Último recurso con configuración mínima
        if not audio_url:
            print("🔄 Método 3: Extracción de emergencia...")
            time.sleep(random.uniform(2, 4))
            audio_url = get_emergency_audio_url(video_url)
        
        elapsed_time = time.time() - start_time
        
        if audio_url:
            print(f"✅ URL de audio obtenida exitosamente en {elapsed_time:.2f}s")
            
            # Actividad Spotify de celebración
            threading.Thread(
                target=spotify_system.get_playlist_tracks,
                daemon=True
            ).start()
            
            return jsonify({
                "success": True, 
                "audio_url": audio_url,
                "extraction_time": round(elapsed_time, 2)
            })
        else:
            print(f"❌ No se pudo obtener URL de audio después de {elapsed_time:.2f}s")
            return jsonify({
                "error": "No se pudo obtener URL de audio válida después de múltiples intentos",
                "extraction_time": round(elapsed_time, 2)
            }), 500
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"💥 Error crítico al obtener audio: {e}")
        return jsonify({
            "error": f"Error del servidor: {str(e)}",
            "extraction_time": round(elapsed_time, 2)
        }), 500

def get_fallback_audio_url(video_url):
    """Método de extracción alternativo con configuración diferente"""
    try:
        print("🛠️  Configurando extractor alternativo...")
        
        # Configuración más permisiva
        ydl_opts = {
            'format': 'worst[ext=mp4]/worst',  # Formato más básico
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'prefer_insecure': True,
            'no_warnings': True,
            'socket_timeout': 60,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'identity',  # Sin compresión
                'Connection': 'keep-alive',
            },
            'extract_flat': False,
            'ignoreerrors': True,
            'geo_bypass': True,
            'geo_bypass_country': 'MX',  # Cambiar país
            'retries': 10,
            'fragment_retries': 10,
            'youtube_include_dash_manifest': False,
            'youtube_include_hls_manifest': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if info and info.get('formats'):
                # Buscar cualquier formato con audio
                for fmt in info['formats']:
                    url = fmt.get('url')
                    if url and fmt.get('acodec') != 'none':
                        print(f"✓ Formato alternativo encontrado: {fmt.get('ext')}")
                        return url
        
        return None
        
    except Exception as e:
        print(f"❌ Error en método alternativo: {e}")
        return None

def get_emergency_audio_url(video_url):
    """Método de emergencia con configuración mínima"""
    try:
        print("🚨 Activando método de emergencia...")
        
        # Configuración ultra básica
        ydl_opts = {
            'format': '18',  # Formato estándar MP4
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': '*/*'
            },
            'ignoreerrors': True,
            'retries': 3,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if info and info.get('url'):
                print("✓ URL de emergencia obtenida")
                return info.get('url')
            elif info and info.get('formats'):
                # Tomar el primer formato disponible
                for fmt in info['formats']:
                    if fmt.get('url'):
                        print(f"✓ Formato de emergencia: {fmt.get('ext', 'unknown')}")
                        return fmt.get('url')
        
        return None
        
    except Exception as e:
        print(f"❌ Error en método de emergencia: {e}")
        return None

def search_songs_stealth(search_term, max_results=15):
    """Búsqueda con máximo sigilo y anti-detección"""
    
    # Verificar cache primero
    cached_results = get_from_cache(search_term)
    if cached_results:
        return cached_results
    
    print(f"Búsqueda sigilosa para: {search_term}")
    start_time = time.time()
    
    # Actividad Spotify durante búsqueda
    threading.Thread(
        target=spotify_system.make_realistic_spotify_search,
        args=(search_term,),
        daemon=True
    ).start()
    
    search_variations = generate_search_variations_optimized(search_term)
    all_results = []
    
    # Búsquedas secuenciales con delays para evitar detección
    for i, variation in enumerate(search_variations):
        try:
            # Aplicar delay entre variaciones
            stealth_system.apply_request_delay()
            
            # Actividad Spotify entre variaciones
            if i > 0 and random.random() < 0.5:
                threading.Thread(
                    target=spotify_system.simulate_user_behavior,
                    daemon=True
                ).start()
            
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
    """Obtener URL directo del audio con múltiples estrategias anti-detección"""
    
    # Estrategias múltiples de extracción
    strategies = [
        'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio',
        'bestaudio/best[height<=480]',
        'worst[ext=webm]/worst[ext=m4a]/worst',
        '18/worst'  # Formato de respaldo
    ]
    
    for i, format_selector in enumerate(strategies):
        try:
            print(f"🔄 Intentando estrategia {i+1}/{len(strategies)}: {format_selector}")
            
            # Configuraciones específicas por estrategia
            ydl_opts = get_enhanced_ydl_opts(format_selector, attempt=i+1)
            
            # Delay adicional entre intentos
            if i > 0:
                delay = random.uniform(2, 5)
                print(f"⏱️  Esperando {delay:.1f}s antes del siguiente intento...")
                time.sleep(delay)
                
                # Actividad Spotify durante reintento
                threading.Thread(
                    target=spotify_system.simulate_user_behavior,
                    daemon=True
                ).start()
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"🎯 Extrayendo info de: {video_url}")
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    print(f"❌ No se obtuvo info en estrategia {i+1}")
                    continue
                
                # Buscar formato de audio válido
                audio_url = extract_best_audio_format(info, strategy_num=i+1)
                if audio_url:
                    print(f"✅ URL de audio obtenida con estrategia {i+1}")
                    return audio_url
                else:
                    print(f"❌ No se encontró formato válido en estrategia {i+1}")
                    
        except Exception as e:
            print(f"❌ Error en estrategia {i+1}: {str(e)}")
            continue
    
    print("💀 Todas las estrategias fallaron")
    return None

def get_enhanced_ydl_opts(format_selector, attempt=1):
    """Configuraciones yt-dlp mejoradas según el intento"""
    
    # Headers más agresivos según el intento
    base_headers = stealth_system.get_stealth_headers()
    
    if attempt == 1:
        # Primera estrategia: Navegador Chrome estándar
        additional_headers = {
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-User': '?1',
        }
    elif attempt == 2:
        # Segunda estrategia: Firefox con diferentes headers
        additional_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
    elif attempt == 3:
        # Tercera estrategia: Móvil Android
        additional_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Sec-Ch-Ua-Mobile': '?1',
        }
    else:
        # Cuarta estrategia: iPad
        additional_headers = {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    # Combinar headers
    final_headers = {**base_headers, **additional_headers}
    
    # Configuraciones específicas por intento
    opts = {
        'format': format_selector,
        'quiet': False if attempt == 1 else True,  # Verbose en primer intento
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'no_warnings': attempt > 1,
        'socket_timeout': 45,
        'http_headers': final_headers,
        'extract_flat': False,  # Extracción completa
        'ignoreerrors': True,
        'geo_bypass': True,
        'geo_bypass_country': ['US', 'GB', 'CA'][attempt % 3],  # Rotar países
        'age_limit': 999,
        'sleep_interval': random.uniform(1, 3),
        'max_sleep_interval': 5,
        'retries': 5,
        'fragment_retries': 5,
        'file_access_retries': 5,
        # Configuraciones anti-throttling
        'throttled_rate': None,
        'ratelimit': None,
        # Configuraciones de extractor específicas
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': False,
    }
    
    # Proxy si está disponible y es un reintento
    if attempt > 1:
        proxy = stealth_system.get_random_proxy()
        if proxy:
            opts['proxy'] = proxy
    
    return opts

def extract_best_audio_format(info, strategy_num=1):
    """Extraer el mejor formato de audio disponible"""
    
    if not info.get('formats'):
        print(f"❌ No hay formatos disponibles")
        return None
    
    formats = info.get('formats', [])
    print(f"📊 {len(formats)} formatos encontrados")
    
    # Prioridades de formato según estrategia
    if strategy_num == 1:
        # Mejor calidad de audio
        preferred_codecs = ['opus', 'aac', 'mp3', 'vorbis']
        preferred_exts = ['webm', 'm4a', 'mp4', 'mp3']
    elif strategy_num == 2:
        # Compatibilidad universal
        preferred_codecs = ['aac', 'mp3', 'opus']
        preferred_exts = ['m4a', 'mp4', 'mp3', 'webm']
    elif strategy_num == 3:
        # Formato más básico
        preferred_codecs = ['aac', 'mp3']
        preferred_exts = ['mp4', 'm4a', 'mp3']
    else:
        # Cualquier formato que funcione
        preferred_codecs = ['aac', 'mp3', 'opus', 'vorbis']
        preferred_exts = ['mp4', 'm4a', 'mp3', 'webm']
    
    # Filtrar formatos solo de audio
    audio_formats = []
    for fmt in formats:
        if (fmt.get('acodec') and fmt.get('acodec') != 'none' and
            fmt.get('url') and 
            (not fmt.get('vcodec') or fmt.get('vcodec') == 'none')):
            audio_formats.append(fmt)
    
    print(f"🎵 {len(audio_formats)} formatos de audio encontrados")
    
    if not audio_formats:
        # Si no hay formatos solo de audio, buscar video con audio
        print("🔄 Buscando formatos de video con audio...")
        for fmt in formats:
            if (fmt.get('acodec') and fmt.get('acodec') != 'none' and
                fmt.get('url') and
                fmt.get('ext') in preferred_exts):
                print(f"✓ Formato encontrado: {fmt.get('ext')} - {fmt.get('acodec')}")
                return fmt.get('url')
    
    # Buscar mejor formato de audio
    for codec in preferred_codecs:
        for ext in preferred_exts:
            for fmt in audio_formats:
                if (codec in fmt.get('acodec', '').lower() and
                    fmt.get('ext') == ext and
                    fmt.get('url') and
                    not fmt.get('url').startswith('https://manifest')):
                    
                    print(f"✓ Formato seleccionado: {ext} - {codec}")
                    return fmt.get('url')
    
    # Fallback: cualquier formato de audio válido
    for fmt in audio_formats:
        if (fmt.get('url') and 
            not fmt.get('url').startswith('https://manifest')):
            print(f"✓ Formato fallback: {fmt.get('ext')} - {fmt.get('acodec')}")
            return fmt.get('url')
    
    print("❌ No se encontró ningún formato de audio válido")
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
    print("🚀 Iniciando servidor Flask con sistema anti-detección avanzado...")
    print("🎵 Integrando autenticación real de Spotify...")
    
    # Probar autenticación Spotify al inicio
    if spotify_system.get_access_token():
        print("✅ Spotify integrado exitosamente")
    else:
        print("⚠️  Advertencia: No se pudo autenticar con Spotify")
    
    print("\n🔒 Características de sigilo activadas:")
    print("   - Rotación de User-Agents")
    print("   - Delays aleatorios entre requests")
    print("   - Headers de navegador real")
    print("   - Búsquedas REALES en Spotify API")
    print("   - Navegación de playlists Spotify")
    print("   - Simulación de comportamiento de usuario")
    print("   - Geo-bypass activado")
    print("   - Cache de búsquedas (5 min)")
    print("   - Token de autenticación Spotify renovable")
    
    print(f"\n🌐 Accede a: http://localhost:8080")
    print("🎯 Sistema de camuflaje Spotify activo")
    
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)