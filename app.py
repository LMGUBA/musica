from flask import Flask, request, render_template, jsonify
import yt_dlp
import ssl
import json
from urllib.parse import quote
import concurrent.futures
import threading
from functools import lru_cache
import time
import random
import requests
from fake_useragent import UserAgent

app = Flask(__name__)

# Deshabilitar verificación SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

# Cache para resultados de búsqueda recientes
search_cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 300  # 5 minutos

# Lista de User Agents rotativos
ua = UserAgent()

# Lista de proxies (opcional - puedes agregar proxies gratuitos)
PROXY_LIST = [
    # Agrega proxies aquí si los tienes
    # 'http://proxy1:port',
    # 'http://proxy2:port',
]

def get_random_headers():
    """Generar headers aleatorios para evitar detección"""
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def get_random_proxy():
    """Obtener proxy aleatorio si está disponible"""
    if PROXY_LIST:
        return random.choice(PROXY_LIST)
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            return render_template("index.html", 
                                 error="Por favor ingresa un término de búsqueda")
        
        try:
            # Buscar canciones sin descargar
            search_results = search_songs_optimized(query)
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
    """Obtener URL de audio directo para reproducción"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "URL no proporcionada"}), 400
        
        print(f"Obteniendo audio para: {video_url}")
        
        # Añadir delay aleatorio para parecer más humano
        time.sleep(random.uniform(0.5, 2.0))
        
        audio_url = get_direct_audio_url_optimized(video_url)
        
        if audio_url:
            print(f"URL de audio obtenida exitosamente")
            return jsonify({"success": True, "audio_url": audio_url})
        else:
            print("No se pudo obtener URL de audio")
            return jsonify({"error": "No se pudo obtener URL de audio válida"}), 500
            
    except Exception as e:
        print(f"Error al obtener audio: {e}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

def get_cache_key(search_term):
    """Generar clave de cache normalizada"""
    return search_term.lower().strip()

def get_from_cache(search_term):
    """Obtener resultados del cache si están disponibles"""
    cache_key = get_cache_key(search_term)
    with cache_lock:
        if cache_key in search_cache:
            cached_data, timestamp = search_cache[cache_key]
            if time.time() - timestamp < CACHE_EXPIRY:
                print(f"Resultados obtenidos del cache para: {search_term}")
                return cached_data
            else:
                # Eliminar entrada expirada
                del search_cache[cache_key]
    return None

def save_to_cache(search_term, results):
    """Guardar resultados en cache"""
    cache_key = get_cache_key(search_term)
    with cache_lock:
        search_cache[cache_key] = (results, time.time())
        # Limitar el tamaño del cache
        if len(search_cache) > 100:
            # Eliminar la entrada más antigua
            oldest_key = min(search_cache.keys(), 
                           key=lambda k: search_cache[k][1])
            del search_cache[oldest_key]

def generate_search_variations_optimized(search_term):
    """Generar variaciones de búsqueda optimizadas"""
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

def search_single_variation(variation, results_per_variation=10):
    """Buscar una sola variación con anti-detección mejorada"""
    search_query = f"ytsearch{results_per_variation}:{variation}"
    
    # Headers y configuración anti-detección
    random_headers = get_random_headers()
    proxy = get_random_proxy()
    
    # Configuración optimizada para evitar detección (yt-dlp 2025.6.9)
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'extract_flat': True,
        'no_warnings': True,
        'socket_timeout': 25,  # Timeout más generoso
        'http_headers': random_headers,
        'sleep_interval': random.uniform(1, 3),  # Delay aleatorio entre requests
        'max_sleep_interval': 5,
        'sleep_interval_subtitles': random.uniform(1, 3),
        'extractor_retries': 3,
        'fragment_retries': 3,
        'skip_unavailable_fragments': True,
        'keep_fragments': False,
        'buffersize': 1024,
        'http_chunk_size': 1024,
        # Configuración adicional para evitar detección
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'age_limit': None,
        'skip_download': True,
        # Nuevas opciones para yt-dlp 2025.6.9
        'no_check_certificates': True,
        'ignore_no_formats_error': True,
        'ignore_errors': True,
        'cookiefile': None,  # No usar cookies
        'no_cookies': True,  # Explícitamente no usar cookies
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash'],  # Evitar formatos complejos
                'player_skip': ['configs'],
            }
        },
    }
    
    # Agregar proxy si está disponible
    if proxy:
        ydl_opts['proxy'] = proxy
    
    try:
        # Delay aleatorio antes de cada búsqueda
        time.sleep(random.uniform(0.5, 2.0))
        
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
        print(f"Error en variación '{variation}': {str(e)}")
        # Si hay error, intentar con configuración más conservadora
        try:
            time.sleep(random.uniform(2, 5))  # Mayor delay en caso de error
            fallback_opts = {
                'quiet': True,
                'noplaylist': True,
                'extract_flat': True,
                'http_headers': get_random_headers(),
                'socket_timeout': 30,
            }
            
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
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
        except:
            return []

def search_songs_optimized(search_term, max_results=15):
    """Búsqueda optimizada con cache y anti-detección"""
    
    # Verificar cache primero
    cached_results = get_from_cache(search_term)
    if cached_results:
        return cached_results
    
    print(f"Búsqueda optimizada para: {search_term}")
    start_time = time.time()
    
    search_variations = generate_search_variations_optimized(search_term)
    all_results = []
    
    # Reducir concurrencia para evitar detección
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_to_variation = {
            executor.submit(search_single_variation, variation, max_results // len(search_variations) + 3): variation 
            for variation in search_variations
        }
        
        for future in concurrent.futures.as_completed(future_to_variation, timeout=30):
            variation = future_to_variation[future]
            try:
                results = future.result()
                all_results.extend(results)
                print(f"Completada búsqueda para: {variation} ({len(results)} resultados)")
                # Delay entre búsquedas completadas
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                print(f"Error en búsqueda paralela para '{variation}': {e}")
    
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
    print(f"Búsqueda completada en {elapsed_time:.2f} segundos - {len(unique_results)} resultados")
    
    return unique_results

def get_best_thumbnail(thumbnails):
    """Obtener la mejor thumbnail disponible"""
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
    """Formatear duración"""
    if not duration or duration == 0:
        return "Desconocido"
    
    try:
        duration = int(duration)
        return f"{duration//60}:{duration%60:02d}"
    except (ValueError, TypeError):
        return "Desconocido"

def clean_string(text):
    """Limpiar strings"""
    if not text:
        return ""
    return str(text).replace("'", "&#39;").replace('"', "&quot;")

def format_views(views):
    """Formatear número de visualizaciones"""
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

@lru_cache(maxsize=50)
def get_direct_audio_url_optimized(video_url):
    """Obtener URL directo del audio con anti-detección mejorada"""
    
    # Configuración anti-detección para extracción de audio
    random_headers = get_random_headers()
    proxy = get_random_proxy()
    
    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best[height<=480]',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'http_headers': random_headers,
        'sleep_interval': random.uniform(1, 2),
        'max_sleep_interval': 3,
        'extractor_retries': 2,
        'fragment_retries': 2,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'age_limit': None,
        # Configuración específica para yt-dlp 2025.6.9
        'no_check_certificates': True,
        'ignore_no_formats_error': True,
        'ignore_errors': False,  # Queremos saber si hay errores aquí
        'cookiefile': None,
        'no_cookies': True,
        'extractor_args': {
            'youtube': {
                'skip': ['hls'],  # Evitar HLS si da problemas
                'player_skip': ['configs'],
                'innertube_host': 'www.youtube.com',
                'innertube_context_client_name': '1',
                'innertube_context_client_version': '2.20210728.00.00',
            }
        },
    }
    
    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        # Delay aleatorio antes de extraer
        time.sleep(random.uniform(1, 3))
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info or not info.get('formats'):
                return None
            
            formats = info.get('formats', [])
            
            # Buscar formato óptimo
            for fmt in formats:
                if (fmt.get('acodec') and fmt.get('acodec') != 'none' and 
                    fmt.get('url') and
                    fmt.get('ext') in ['webm', 'm4a', 'mp4'] and
                    not fmt.get('url').startswith('https://manifest')):
                    
                    return fmt.get('url')
            
            return None
            
    except Exception as e:
        print(f"Error obteniendo URL de audio: {e}")
        # Intentar con configuración más básica
        try:
            time.sleep(random.uniform(2, 4))
            basic_opts = {
                'format': 'best[height<=360]/best',
                'quiet': True,
                'http_headers': get_random_headers(),
            }
            
            with yt_dlp.YoutubeDL(basic_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if info and info.get('url'):
                    return info.get('url')
        except:
            pass
        
        return None

# Manejo de errores global
@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Error interno del servidor"), 500

if __name__ == "__main__":
    print("Iniciando servidor Flask con anti-detección...")
    print("Accede a: http://localhost:8080")
    print("Características anti-detección:")
    print("- User Agents aleatorios")
    print("- Headers rotativos")
    print("- Delays aleatorios")
    print("- Reintentos con fallback")
    print("- Geo-bypass activado")
    print("- Configuración conservadora para evitar detección")
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)