from flask import Flask, request, render_template, jsonify
import requests
import json
import time
import random
import os
from urllib.parse import quote_plus, urlparse
import concurrent.futures
import threading
from functools import lru_cache

app = Flask(__name__)

# Cache para resultados
search_cache = {}
cache_lock = threading.Lock()
CACHE_EXPIRY = 300

# Lista de instancias públicas de Invidious (más estables)
INVIDIOUS_INSTANCES = [
    "https://invidious.projectsegfau.lt",
    "https://invidious.flokinet.to",
    "https://invidious.privacydev.net",
    "https://inv.tux.pizza",
    "https://invidious.drgns.space",
    "https://iv.ggtyler.dev",
    "https://invidious.io.lol",
    "https://invidious.private.coffee"
]

# Proxies públicos gratuitos (rotativos)
FREE_PROXIES = [
    # Estos son ejemplos, necesitas obtener proxies actualizados
    "http://proxy-server.com:8080",
    "http://another-proxy.com:3128",
    # Agregar más proxies según disponibilidad
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
]

IS_RAILWAY = os.environ.get('RAILWAY_ENVIRONMENT') is not None

def get_working_instance():
    """Obtener una instancia de Invidious que funcione"""
    random.shuffle(INVIDIOUS_INSTANCES)
    
    for instance in INVIDIOUS_INSTANCES:
        try:
            response = requests.get(f"{instance}/api/v1/stats", timeout=5)
            if response.status_code == 200:
                print(f"Instancia funcionando: {instance}")
                return instance
        except:
            continue
    
    return None

def create_session_with_proxy():
    """Crear sesión con proxy rotativo"""
    session = requests.Session()
    
    # Headers estándar
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    
    # Usar proxy si está disponible
    if FREE_PROXIES and random.choice([True, False]):
        proxy = random.choice(FREE_PROXIES)
        session.proxies = {
            'http': proxy,
            'https': proxy
        }
        print(f"Usando proxy: {proxy}")
    
    return session

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            return render_template("index.html", 
                                 error="Por favor ingresa un término de búsqueda")
        
        try:
            search_results = search_songs_invidious(query)
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
    """Obtener URL de audio usando Invidious API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "URL no proporcionada"}), 400
        
        # Extraer video ID de la URL
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "ID de video inválido"}), 400
        
        print(f"Obteniendo audio para video ID: {video_id}")
        
        # Intentar múltiples métodos
        audio_url = None
        
        # Método 1: Invidious API
        audio_url = get_audio_from_invidious(video_id)
        
        # Método 2: Invidious directo con diferentes instancias
        if not audio_url:
            audio_url = get_audio_from_invidious_direct(video_id)
        
        # Método 3: YouTube directo con proxies
        if not audio_url:
            audio_url = get_audio_youtube_proxy(video_id)
        
        if audio_url:
            return jsonify({"success": True, "audio_url": audio_url})
        else:
            return jsonify({
                "error": "No se pudo obtener el audio. Intenta con otra canción.",
                "suggestion": "El video puede estar restringido geográficamente"
            }), 503
            
    except Exception as e:
        print(f"Error al obtener audio: {e}")
        return jsonify({
            "error": f"Error del servidor: {str(e)}",
            "suggestion": "Intenta nuevamente"
        }), 500

def extract_video_id(url):
    """Extraer ID del video de YouTube"""
    if 'youtube.com/watch?v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    elif len(url) == 11:  # ID directo
        return url
    return None

def get_audio_from_invidious(video_id):
    """Obtener audio usando Invidious API"""
    working_instance = get_working_instance()
    if not working_instance:
        return None
    
    try:
        session = create_session_with_proxy()
        url = f"{working_instance}/api/v1/videos/{video_id}"
        
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # Buscar formato de audio
        if 'adaptiveFormats' in data:
            for fmt in data['adaptiveFormats']:
                if (fmt.get('type', '').startswith('audio') and 
                    fmt.get('url') and
                    'webm' in fmt.get('type', '')):
                    return fmt['url']
        
        # Fallback a formatStreams
        if 'formatStreams' in data:
            for fmt in data['formatStreams']:
                if fmt.get('url'):
                    return fmt['url']
        
        return None
        
    except Exception as e:
        print(f"Error con Invidious API: {e}")
        return None

def get_audio_from_invidious_direct(video_id):
    """Método directo usando múltiples instancias de Invidious"""
    for instance in INVIDIOUS_INSTANCES[:4]:  # Probar solo las primeras 4
        try:
            session = create_session_with_proxy()
            
            # URL directa del audio desde Invidious
            audio_url = f"{instance}/latest_version?id={video_id}&itag=140"
            
            # Verificar si la URL funciona
            head_response = session.head(audio_url, timeout=10)
            if head_response.status_code == 200:
                return audio_url
                
        except Exception as e:
            print(f"Error con instancia {instance}: {e}")
            continue
    
    return None

def get_audio_youtube_proxy(video_id):
    """Obtener audio de YouTube usando proxy"""
    try:
        session = create_session_with_proxy()
        
        # URLs alternativas para obtener info del video
        urls_to_try = [
            f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
            f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}",
        ]
        
        for url in urls_to_try:
            try:
                response = session.get(url, timeout=10)
                if response.status_code == 200:
                    # Si obtenemos info del video, construir URL directa
                    return f"https://www.youtube.com/watch?v={video_id}"
            except:
                continue
        
        return None
        
    except Exception as e:
        print(f"Error con YouTube proxy: {e}")
        return None

def search_songs_invidious(search_term, max_results=15):
    """Buscar canciones usando Invidious API"""
    
    # Verificar cache
    cached_results = get_from_cache(search_term)
    if cached_results:
        return cached_results
    
    working_instance = get_working_instance()
    if not working_instance:
        return []
    
    try:
        session = create_session_with_proxy()
        
        # URL de búsqueda en Invidious
        search_url = f"{working_instance}/api/v1/search"
        params = {
            'q': search_term,
            'type': 'video',
            'sort_by': 'relevance'
        }
        
        response = session.get(search_url, params=params, timeout=15)
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        
        for item in data[:max_results]:
            if item.get('type') == 'video':
                result = {
                    'title': clean_string(item.get('title', 'Título desconocido')),
                    'uploader': clean_string(item.get('author', 'Canal desconocido')),
                    'duration': format_duration(item.get('lengthSeconds', 0)),
                    'view_count': format_views(item.get('viewCount', 0)),
                    'url': f"https://www.youtube.com/watch?v={item.get('videoId', '')}",
                    'thumbnail': get_invidious_thumbnail(item, working_instance),
                    'id': item.get('videoId', ''),
                    'upload_date': ''
                }
                results.append(result)
        
        # Guardar en cache
        save_to_cache(search_term, results)
        
        print(f"Búsqueda Invidious completada - {len(results)} resultados")
        return results
        
    except Exception as e:
        print(f"Error en búsqueda Invidious: {e}")
        return []

def get_invidious_thumbnail(item, instance):
    """Obtener thumbnail desde Invidious"""
    video_id = item.get('videoId', '')
    if video_id:
        return f"{instance}/vi/{video_id}/mqdefault.jpg"
    return ""

def get_from_cache(search_term):
    """Obtener del cache"""
    cache_key = search_term.lower().strip()
    with cache_lock:
        if cache_key in search_cache:
            cached_data, timestamp = search_cache[cache_key]
            if time.time() - timestamp < CACHE_EXPIRY:
                return cached_data
            else:
                del search_cache[cache_key]
    return None

def save_to_cache(search_term, results):
    """Guardar en cache"""
    cache_key = search_term.lower().strip()
    with cache_lock:
        search_cache[cache_key] = (results, time.time())
        if len(search_cache) > 50:
            oldest_key = min(search_cache.keys(), 
                           key=lambda k: search_cache[k][1])
            del search_cache[oldest_key]

def clean_string(text):
    """Limpiar strings"""
    if not text:
        return ""
    return str(text).replace("'", "&#39;").replace('"', "&quot;")

def format_duration(duration):
    """Formatear duración"""
    if not duration:
        return "Desconocido"
    
    try:
        duration = int(duration)
        return f"{duration//60}:{duration%60:02d}"
    except:
        return "Desconocido"

def format_views(views):
    """Formatear visualizaciones"""
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
    except:
        return "0"

@app.route("/health")
def health_check():
    """Health check"""
    working_instance = get_working_instance()
    return jsonify({
        "status": "healthy" if working_instance else "degraded",
        "invidious_instance": working_instance,
        "railway_mode": IS_RAILWAY
    })

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Error interno del servidor"), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    print("Iniciando servidor con Invidious API...")
    print(f"Puerto: {port}")
    print(f"Modo Railway: {IS_RAILWAY}")
    print("Características:")
    print("- API de Invidious para mayor estabilidad")
    print("- Proxies rotativos opcionales")
    print("- Múltiples instancias de respaldo")
    print("- Sin dependencia de yt-dlp")
    
    app.run(
        debug=False if IS_RAILWAY else True,
        host='0.0.0.0',
        port=port,
        threaded=True
    )