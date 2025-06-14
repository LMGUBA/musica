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
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# Deshabilitar verificación SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

# Cache para resultados de búsqueda recientes
search_cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 300  # 5 minutos

# Lista expandida de User Agents para Railway
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
]

# Detectar si estamos en Railway
IS_RAILWAY = os.environ.get('RAILWAY_ENVIRONMENT') is not None

# Configuración específica para Railway
RAILWAY_CONFIG = {
    'socket_timeout': 45 if IS_RAILWAY else 20,
    'max_workers': 2 if IS_RAILWAY else 3,
    'retry_attempts': 3 if IS_RAILWAY else 2,
    'delay_between_requests': 2 if IS_RAILWAY else 0.5
}

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
    """Obtener URL de audio directo para reproducción con múltiples intentos optimizado para Railway"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "URL no proporcionada"}), 400
        
        print(f"Obteniendo audio para: {video_url} (Railway: {IS_RAILWAY})")
        
        # Método específico para Railway con delays y reintentos
        audio_url = None
        
        for attempt in range(RAILWAY_CONFIG['retry_attempts']):
            print(f"Intento {attempt + 1}/{RAILWAY_CONFIG['retry_attempts']}")
            
            # Agregar delay entre intentos en Railway
            if attempt > 0 and IS_RAILWAY:
                time.sleep(RAILWAY_CONFIG['delay_between_requests'])
            
            # Método 1: Configuración Railway-optimizada
            audio_url = get_direct_audio_url_railway_optimized(video_url)
            
            if audio_url:
                break
                
            # Método 2: Fallback con configuración más permisiva
            if not audio_url:
                print(f"Método 1 falló en intento {attempt + 1}, probando fallback...")
                audio_url = get_audio_url_railway_fallback(video_url)
            
            if audio_url:
                break
                
            # Método 3: Último recurso con configuración mínima
            if not audio_url and attempt == RAILWAY_CONFIG['retry_attempts'] - 1:
                print("Último intento con configuración mínima...")
                audio_url = get_audio_url_minimal(video_url)
        
        if audio_url:
            print(f"URL de audio obtenida exitosamente después de {attempt + 1} intento(s)")
            return jsonify({"success": True, "audio_url": audio_url})
        else:
            print("Todos los métodos y reintentos fallaron")
            return jsonify({
                "error": "Servicio temporalmente no disponible. YouTube puede estar bloqueando las peticiones.",
                "suggestion": "Intenta con otra canción o espera unos minutos",
                "railway_mode": IS_RAILWAY
            }), 503
            
    except Exception as e:
        print(f"Error al obtener audio: {e}")
        return jsonify({
            "error": f"Error del servidor: {str(e)}",
            "suggestion": "Intenta nuevamente en unos momentos",
            "railway_mode": IS_RAILWAY
        }), 500

def get_random_user_agent():
    """Obtener un User Agent aleatorio con más variedad para Railway"""
    return random.choice(USER_AGENTS)

def get_random_ip_headers():
    """Generar headers adicionales para simular diferentes IPs"""
    return {
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def create_requests_session():
    """Crear sesión de requests con reintentos para Railway"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

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
        if len(search_cache) > 50:  # Reducido para Railway
            # Eliminar la entrada más antigua
            oldest_key = min(search_cache.keys(), 
                           key=lambda k: search_cache[k][1])
            del search_cache[oldest_key]

def generate_search_variations_optimized(search_term):
    """Generar variaciones de búsqueda optimizadas para Railway"""
    # Menos variaciones para Railway
    variations = [search_term]
    
    if len(search_term) > 3 and not IS_RAILWAY:
        variations.append(f"{search_term} oficial")
    
    return variations[:2] if IS_RAILWAY else variations[:3]

def search_single_variation(variation, results_per_variation=8):
    """Buscar una sola variación optimizada para Railway"""
    search_query = f"ytsearch{results_per_variation}:{variation}"
    
    # Headers adicionales para Railway
    headers = {
        'User-Agent': get_random_user_agent()
    }
    
    if IS_RAILWAY:
        headers.update(get_random_ip_headers())
    
    # Configuración específica para Railway
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'extract_flat': True,
        'no_warnings': True,
        'socket_timeout': RAILWAY_CONFIG['socket_timeout'],
        'http_headers': headers,
        'retries': 2 if IS_RAILWAY else 1,
        'fragment_retries': 2 if IS_RAILWAY else 1,
        'ignoreerrors': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US'
    }
    
    try:
        # Delay adicional en Railway
        if IS_RAILWAY:
            time.sleep(random.uniform(0.5, 1.5))
            
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
        return []

def search_songs_optimized(search_term, max_results=12):
    """Búsqueda optimizada para Railway"""
    
    # Verificar cache primero
    cached_results = get_from_cache(search_term)
    if cached_results:
        return cached_results
    
    print(f"Búsqueda optimizada para: {search_term} (Railway: {IS_RAILWAY})")
    start_time = time.time()
    
    search_variations = generate_search_variations_optimized(search_term)
    all_results = []
    
    # Configuración de workers adaptada para Railway
    max_workers = RAILWAY_CONFIG['max_workers']
    
    # Usar ThreadPoolExecutor con menos workers en Railway
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_variation = {
            executor.submit(search_single_variation, variation, max_results // len(search_variations) + 2): variation 
            for variation in search_variations
        }
        
        # Timeout más largo para Railway
        timeout = 30 if IS_RAILWAY else 15
        
        for future in concurrent.futures.as_completed(future_to_variation, timeout=timeout):
            variation = future_to_variation[future]
            try:
                results = future.result()
                all_results.extend(results)
                print(f"Completada búsqueda para: {variation} ({len(results)} resultados)")
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

def get_direct_audio_url_railway_optimized(video_url):
    """Obtener URL directo del audio optimizado específicamente para Railway"""
    
    # Headers adicionales para Railway
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    if IS_RAILWAY:
        headers.update(get_random_ip_headers())
    
    ydl_opts = {
        'format': 'bestaudio[filesize<25M]/bestaudio[ext=webm]/bestaudio[ext=m4a]/worst[acodec!=none]',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'no_warnings': True,
        'socket_timeout': RAILWAY_CONFIG['socket_timeout'],
        'http_headers': headers,
        'retries': 3 if IS_RAILWAY else 2,
        'fragment_retries': 3 if IS_RAILWAY else 2,
        'ignoreerrors': True,
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'extractor_args': {
            'youtube': {
                'skip': ['dash'] if IS_RAILWAY else ['dash', 'hls'],
                'player_skip': ['configs']
            }
        }
    }

    try:
        # Delay específico para Railway
        if IS_RAILWAY:
            time.sleep(random.uniform(1, 2))
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info or not info.get('formats'):
                return None
            
            formats = info.get('formats', [])
            
            # Filtros específicos para Railway
            for fmt in formats:
                if (fmt.get('acodec') and fmt.get('acodec') != 'none' and 
                    fmt.get('url') and
                    fmt.get('ext') in ['webm', 'm4a', 'mp4'] and
                    not fmt.get('url').startswith('https://manifest') and
                    fmt.get('filesize_approx', 0) < 25000000):  # Límite reducido para Railway
                    
                    return fmt.get('url')
            
            return None
            
    except Exception as e:
        print(f"Error método Railway optimizado: {e}")
        return None

def get_audio_url_railway_fallback(video_url):
    """Método fallback específico para Railway"""
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Referer': 'https://www.youtube.com/'
    }
    
    ydl_opts = {
        'format': 'worst[acodec!=none]/worstaudio/worst',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'no_warnings': True,
        'socket_timeout': RAILWAY_CONFIG['socket_timeout'] + 10,
        'http_headers': headers,
        'retries': 2,
        'ignoreerrors': True
    }

    try:
        if IS_RAILWAY:
            time.sleep(random.uniform(0.5, 1))
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                return None
            
            # Buscar cualquier formato válido
            if info.get('url'):
                return info.get('url')
            
            formats = info.get('formats', [])
            for fmt in formats:
                if fmt.get('url'):
                    return fmt.get('url')
            
            return None
            
    except Exception as e:
        print(f"Error método Railway fallback: {e}")
        return None

def get_audio_url_minimal(video_url):
    """Método mínimo para casos extremos"""
    ydl_opts = {
        'format': 'best/worst',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 60,
        'retries': 1,
        'http_headers': {
            'User-Agent': get_random_user_agent()
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url') if info else None
            
    except Exception as e:
        print(f"Error método mínimo: {e}")
        return None

# Manejo de errores global
@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Error interno del servidor"), 500

@app.route("/health")
def health_check():
    """Endpoint de salud para Railway"""
    return jsonify({
        "status": "healthy",
        "railway_mode": IS_RAILWAY,
        "timestamp": time.time()
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    print(f"Iniciando servidor Flask optimizado para Railway...")
    print(f"Puerto: {port}")
    print(f"Modo Railway: {IS_RAILWAY}")
    print("Optimizaciones implementadas:")
    print("- Detección automática de Railway")
    print("- Timeouts y reintentos adaptativos")
    print("- Headers anti-bloqueo mejorados")
    print("- Delays inteligentes entre peticiones")
    print("- Gestión de recursos optimizada")
    
    app.run(
        debug=False if IS_RAILWAY else True, 
        host='0.0.0.0', 
        port=port, 
        threaded=True
    )