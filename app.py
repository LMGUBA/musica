from flask import Flask, request, render_template, jsonify
import yt_dlp
import ssl
import json
from urllib.parse import quote
import concurrent.futures
import threading
from functools import lru_cache
import time

app = Flask(__name__)

# Deshabilitar verificación SSL globalmente
ssl._create_default_https_context = ssl._create_unverified_context

# Cache para resultados de búsqueda recientes
search_cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 300  # 5 minutos

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
    # Reducir número de variaciones para mayor velocidad
    variations = [search_term]
    
    # Solo agregar variaciones más efectivas
    if len(search_term) > 3:  # Evitar variaciones para términos muy cortos
        variations.append(f"{search_term} oficial")
        
        # Variaciones específicas solo para artistas conocidos
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
                break  # Solo una variación por artista
    
    return variations[:3]  # Limitar a máximo 3 variaciones

def search_single_variation(variation, results_per_variation=10):
    """Buscar una sola variación de forma optimizada"""
    search_query = f"ytsearch{results_per_variation}:{variation}"
    
    # Configuración optimizada para velocidad
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'extract_flat': True,  # Extracción plana para mayor velocidad
        'no_warnings': True,
        'socket_timeout': 10,  # Timeout reducido
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
            results = []
            if 'entries' in info and info['entries']:
                for entry in info['entries'][:results_per_variation]:
                    if entry and entry.get('title') and entry.get('url'):
                        # Obtener información adicional solo si es necesario
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

def search_songs_optimized(search_term, max_results=15):
    """Búsqueda optimizada con cache y concurrencia"""
    
    # Verificar cache primero
    cached_results = get_from_cache(search_term)
    if cached_results:
        return cached_results
    
    print(f"Búsqueda optimizada para: {search_term}")
    start_time = time.time()
    
    search_variations = generate_search_variations_optimized(search_term)
    all_results = []
    
    # Usar ThreadPoolExecutor para búsquedas concurrentes
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Enviar todas las búsquedas en paralelo
        future_to_variation = {
            executor.submit(search_single_variation, variation, max_results // len(search_variations) + 3): variation 
            for variation in search_variations
        }
        
        # Recopilar resultados conforme van completándose
        for future in concurrent.futures.as_completed(future_to_variation, timeout=15):
            variation = future_to_variation[future]
            try:
                results = future.result()
                all_results.extend(results)
                print(f"Completada búsqueda para: {variation} ({len(results)} resultados)")
            except Exception as e:
                print(f"Error en búsqueda paralela para '{variation}': {e}")
    
    # Eliminar duplicados de forma eficiente
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
    """Obtener la mejor thumbnail disponible de forma eficiente"""
    if not thumbnails:
        return ""
    
    # Priorizar thumbnails de calidad media para balance entre calidad y velocidad
    for thumb in thumbnails:
        if thumb.get('url') and 'mqdefault' in thumb.get('url', ''):
            return thumb['url']
    
    # Fallback a la primera disponible
    for thumb in thumbnails:
        if thumb.get('url'):
            return thumb['url']
    
    return ""

def format_duration(duration):
    """Formatear duración de forma eficiente"""
    if not duration or duration == 0:
        return "Desconocido"
    
    try:
        duration = int(duration)
        return f"{duration//60}:{duration%60:02d}"
    except (ValueError, TypeError):
        return "Desconocido"

def clean_string(text):
    """Limpiar strings de forma optimizada"""
    if not text:
        return ""
    return str(text).replace("'", "&#39;").replace('"', "&quot;")

def format_views(views):
    """Formatear número de visualizaciones de forma optimizada"""
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
    """Obtener URL directo del audio con cache LRU"""
    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio',
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'prefer_insecure': True,
        'no_warnings': True,
        'socket_timeout': 15,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info or not info.get('formats'):
                return None
            
            # Buscar formato óptimo más rápido
            formats = info.get('formats', [])
            
            # Priorizar formatos conocidos por compatibilidad
            for fmt in formats:
                if (fmt.get('acodec') and fmt.get('acodec') != 'none' and 
                    fmt.get('url') and
                    fmt.get('ext') in ['webm', 'm4a', 'mp4'] and
                    not fmt.get('url').startswith('https://manifest')):
                    
                    return fmt.get('url')
            
            return None
            
    except Exception as e:
        print(f"Error obteniendo URL de audio: {e}")
        return None

# Manejo de errores global
@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Error interno del servidor"), 500

if __name__ == "__main__":
    print("Iniciando servidor Flask optimizado...")
    print("Accede a: http://localhost:8080")
    print("Optimizaciones activadas:")
    print("- Cache de búsquedas (5 min)")
    print("- Búsquedas concurrentes")
    print("- Extracción plana para mayor velocidad")
    print("- Timeouts optimizados")
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)