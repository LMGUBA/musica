import random
import time
from flask import Flask, request, render_template, jsonify
import yt_dlp
import ssl
import requests
import base64

app = Flask(__name__)

# Deshabilitar verificación SSL
ssl._create_default_https_context = ssl._create_unverified_context

# Configuración simple de Spotify
SPOTIFY_CLIENT_ID = "c508ae6a444f4d16877ba4dcecbba1ab"
SPOTIFY_CLIENT_SECRET = "66c896d517ec497dad0d59f00fed258c"

# Variables globales para token Spotify
spotify_token = None
spotify_token_expiry = None

def get_spotify_token():
    """Obtiene token de Spotify - IGUAL que FastAPI"""
    global spotify_token, spotify_token_expiry
    
    current_time = int(time.time())
    
    if spotify_token and spotify_token_expiry and current_time < spotify_token_expiry:
        return spotify_token
    
    try:
        credentials = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
        
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={"grant_type": "client_credentials"}
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        spotify_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        spotify_token_expiry = current_time + expires_in
        
        return spotify_token
    except Exception as e:
        print(f"Error en autenticación de Spotify: {str(e)}")
        return None

def search_spotify_track(query):
    """Busca en Spotify - IGUAL que FastAPI"""
    try:
        token = get_spotify_token()
        if not token:
            return None
        
        response = requests.get(
            f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if not data.get("tracks") or not data["tracks"].get("items"):
            return None
        
        track = data["tracks"]["items"][0]
        return {
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "albumArt": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotifyUrl": track["external_urls"]["spotify"]
        }
    except Exception as e:
        print(f"Error al buscar en Spotify: {str(e)}")
        return None

def enhance_with_spotify_data(youtube_results):
    """Enriquece resultados - IGUAL que FastAPI"""
    if not youtube_results:
        return []
    
    enhanced_results = []
    
    for video in youtube_results:
        try:
            spotify_data = search_spotify_track(video["title"])
            
            if spotify_data:
                video["thumbnail"] = spotify_data["albumArt"] or video["thumbnail"]
                video["spotifyInfo"] = {
                    "artist": spotify_data["artist"],
                    "album": spotify_data["album"],
                    "spotifyUrl": spotify_data["spotifyUrl"]
                }
            
            enhanced_results.append(video)
        except Exception as e:
            print(f"Error al enriquecer datos: {str(e)}")
            enhanced_results.append(video)
    
    return enhanced_results

def search_youtube_simple(query):
    """Búsqueda simple - COPIANDO la lógica de FastAPI"""
    try:
        # EXACTAMENTE como FastAPI
        music_query = f"ytsearch15:{query}"
        
        # Configuración SIMPLE como FastAPI
        ydl_opts = {
            "quiet": False,  # Como FastAPI
            "noplaylist": True,
            "extract_flat": True,  # ¡CLAVE! Como FastAPI
            "skip_download": True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Searching for: {music_query}")
            info = ydl.extract_info(music_query, download=False)
            
            if not info or 'entries' not in info:
                return []
            
            # Filtrado SIMPLE como FastAPI
            valid_videos = []
            for entry in info["entries"]:
                if not entry:
                    continue
                
                # Solo filtrar contenido adulto como FastAPI
                if entry.get("age_limit", 0) > 18:
                    continue
                
                valid_videos.append({
                    "title": entry.get("title", ""),
                    "videoId": entry.get("id", ""),
                    "duration": entry.get("duration", 0),
                    "thumbnail": entry.get("thumbnail", ""),
                    "channel": entry.get("channel", ""),
                    "url": f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                })
                
                if len(valid_videos) >= 10:
                    break
            
            print(f"Found {len(valid_videos)} valid videos")
            
            # Enriquecer con Spotify como FastAPI
            enhanced_results = enhance_with_spotify_data(valid_videos)
            return enhanced_results
            
    except Exception as e:
        print(f"Error in search_youtube_simple: {str(e)}")
        return []

def get_direct_audio_url_simple(video_url):
    """Extracción de audio SIMPLE - sin sobre-ingeniería"""
    try:
        # Configuración BÁSICA y efectiva
        ydl_opts = {
            'format': 'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio',
            'quiet': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'extract_flat': False,  # Para audio necesitamos extracción completa
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                return None
            
            # Buscar formato de audio
            if info.get('formats'):
                for fmt in info['formats']:
                    if (fmt.get('acodec') and fmt.get('acodec') != 'none' and
                        fmt.get('url') and
                        (not fmt.get('vcodec') or fmt.get('vcodec') == 'none')):
                        return fmt.get('url')
            
            # Fallback: URL directa si está disponible
            if info.get('url'):
                return info.get('url')
        
        return None
        
    except Exception as e:
        print(f"Error obteniendo audio: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            return render_template("index.html", 
                                 error="Por favor ingresa un término de búsqueda")
        
        try:
            # Búsqueda simple sin complicaciones
            search_results = search_youtube_simple(query)
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
    """Obtener URL de audio - SIMPLE y efectivo"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        video_url = data.get("video_url")
        if not video_url:
            return jsonify({"error": "URL no proporcionada"}), 400
        
        print(f"Obteniendo audio para: {video_url}")
        
        # UNA SOLA estrategia simple
        audio_url = get_direct_audio_url_simple(video_url)
        
        if audio_url:
            print("✅ URL de audio obtenida exitosamente")
            return jsonify({
                "success": True, 
                "audio_url": audio_url
            })
        else:
            print("❌ No se pudo obtener URL de audio")
            return jsonify({
                "error": "No se pudo obtener URL de audio"
            }), 500
            
    except Exception as e:
        print(f"Error al obtener audio: {e}")
        return jsonify({
            "error": f"Error del servidor: {str(e)}"
        }), 500

# Funciones auxiliares simples
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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html', error="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html', error="Error interno del servidor"), 500

if __name__ == "__main__":
    print("🚀 Iniciando servidor Flask SIMPLIFICADO...")
    print("✅ Copiando lógica exitosa de FastAPI")
    print("🎵 Spotify integrado de forma simple")
    print("🔑 Características:")
    print("   - extract_flat=True para búsquedas")
    print("   - Configuración yt-dlp simple")
    print("   - Sin rotación agresiva de headers")
    print("   - Sin múltiples estrategias")
    print("   - Comportamiento natural")
    
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)