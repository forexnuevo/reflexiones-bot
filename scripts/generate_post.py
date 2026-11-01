#!/usr/bin/env python3
"""
Generador automatico de posts para Facebook - Reflexiones Religiosas
Usa Groq (GRATIS) para texto + Replicate REST API para imagenes + Facebook Graph API
"""

import os
import random
import requests
import json
import sys
import time
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    os.system("pip install openai --quiet")
    from openai import OpenAI

# ============================================================
# CONFIGURACION
# ============================================================
PAGE_ID = "102300045081467"
PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

# Modelos Groq en orden de preferencia
GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
]

# Palabras clave para EXCLUIR modelos que no sirven para texto
SKIP_MODEL_KEYWORDS = ["whisper", "tts", "orpheus", "guard", "safeguard", "arabic", "stt", "vision", "prompt-guard"]

# ============================================================
# PAIN POINTS
# ============================================================
PAIN_POINTS = [
    {
        "tema": "soledad",
        "peso": 25,
        "prompt_texto": "Escribe una publicacion emotiva y corta para Facebook sobre sentirse solo y encontrar esperanza en Dios. Incluye: una primera linea impactante, un versiculo biblico, una oracion breve, y termina con 'Escribe AMEN si crees que Dios esta contigo'. Sin hashtags. En espanol. Maximo 200 palabras.",
        "prompt_imagen": "peaceful divine golden light rays shining through dark forest clearing, person kneeling in prayer silhouette, warm and ethereal atmosphere, spiritual hope, photorealistic"
    },
    {
        "tema": "familia_en_crisis",
        "peso": 25,
        "prompt_texto": "Escribe una publicacion corta y poderosa para Facebook sobre familias que pasan por momentos dificiles. Incluye: apertura empatica, versiculo biblico sobre restauracion familiar, oracion de union, y termina con 'Etiqueta a alguien que necesita esta bendicion'. Sin hashtags. En espanol. Maximo 200 palabras.",
        "prompt_imagen": "family silhouette at golden sunset, parents and children holding hands, warm orange and purple sky, unity and love, heartwarming scene, photorealistic"
    },
    {
        "tema": "dificultades_economicas",
        "peso": 20,
        "prompt_texto": "Escribe una publicacion inspiradora para Facebook para personas con dificultades economicas. Incluye: apertura que resuene con quien tiene deudas o trabajo perdido, Filipenses 4:19 o similar, declaracion de fe, y termina con 'Escribe SI si crees que Dios provee'. Sin hashtags. En espanol. Maximo 200 palabras.",
        "prompt_imagen": "hands open receiving divine golden light from above, abundance and blessing, peaceful and hopeful, spiritual provision concept, photorealistic"
    },
    {
        "tema": "duelo_y_perdida",
        "peso": 15,
        "prompt_texto": "Escribe una publicacion consoladora para Facebook para personas que perdieron a un ser querido. Incluye: apertura tierna, Juan 11:25 o similar sobre vida eterna, oracion de consuelo, y termina con 'Comparte si conoces a alguien que necesita esta paz'. Sin hashtags. En espanol. Maximo 200 palabras.",
        "prompt_imagen": "white dove flying into bright heavenly light, peaceful memorial candle, soft flowers, sunrise breaking through gentle clouds, hope and eternal life, photorealistic"
    },
    {
        "tema": "abandono_espiritual",
        "peso": 15,
        "prompt_texto": "Escribe una publicacion honesta para Facebook sobre sentir que Dios esta lejos. Incluye: apertura que valide ese sentimiento, Isaias 41:10 o similar, declaracion de fe, y termina con 'Escribe CONFIO SI aun en el silencio confias en El'. Sin hashtags. En espanol. Maximo 200 palabras.",
        "prompt_imagen": "person standing alone in dark valley looking up at single powerful beam of divine light breaking through dramatic storm clouds, spiritual awakening, hope in darkness, photorealistic"
    }
]


def seleccionar_pain_point():
    temas = [p["tema"] for p in PAIN_POINTS]
    pesos = [p["peso"] for p in PAIN_POINTS]
    tema_elegido = random.choices(temas, weights=pesos, k=1)[0]
    return next(p for p in PAIN_POINTS if p["tema"] == tema_elegido)


def es_modelo_texto(model_id):
    """Filtra modelos que NO son para generacion de texto"""
    low = model_id.lower()
    return not any(kw in low for kw in SKIP_MODEL_KEYWORDS)


def obtener_modelo_groq():
    """Detecta que modelo Groq esta disponible en esta cuenta"""
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=10
        )
        if r.ok:
            all_models = [m["id"] for m in r.json().get("data", [])]
            available = [m for m in all_models if es_modelo_texto(m)]
            print(f"  Modelos de texto disponibles: {available}")
            for preferred in GROQ_MODELS:
                if preferred in available:
                    print(f"  Usando modelo: {preferred}")
                    return preferred
            if available:
                print(f"  Usando primer modelo de texto: {available[0]}")
                return available[0]
            # Si ningun modelo pasa el filtro, usar el primero de todos
            if all_models:
                print(f"  Fallback: {all_models[0]}")
                return all_models[0]
    except Exception as e:
        print(f"  Advertencia al consultar modelos Groq: {e}")
    return GROQ_MODELS[0]


def texto_es_valido(texto):
    """Verifica que el texto no tenga repeticiones anormales o contenido basura"""
    if not texto or len(texto.strip()) < 100:
        return False, "texto muy corto"
    palabras = texto.lower().split()
    if len(palabras) > 10:
        from collections import Counter
        conteo = Counter(palabras)
        for palabra, count in conteo.items():
            if len(palabra) <= 4 and count > 15:
                return False, f"palabra '{palabra}' repetida {count} veces"
        for i in range(len(palabras) - 3):
            if palabras[i] == palabras[i+1] == palabras[i+2] == palabras[i+3]:
                return False, f"repeticion consecutiva de '{palabras[i]}'"
    return True, "ok"


def generar_texto(pain_point):
    """Genera el texto del post con Groq - con auto-deteccion de modelo y reintento"""
    # Obtener lista de modelos de texto disponibles
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=10
        )
        all_models = [m["id"] for m in r.json().get("data", [])] if r.ok else []
        text_models = [m for m in all_models if es_modelo_texto(m)]
        # Ordenar por preferencia
        ordered = [m for m in GROQ_MODELS if m in text_models]
        ordered += [m for m in text_models if m not in ordered]
        modelos_a_probar = ordered if ordered else GROQ_MODELS[:3]
    except:
        modelos_a_probar = GROQ_MODELS[:3]

    print(f"  Modelos a probar: {modelos_a_probar}")
    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    prompt = pain_point["prompt_texto"]

    for modelo in modelos_a_probar:
        try:
            print(f"  Probando modelo: {modelo}...")
            response = client.chat.completions.create(
                model=modelo,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un escritor cristiano que crea contenido espiritual autentico y emotivo en espanol para Facebook. Escribe en parrafos naturales, sin hashtags."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.8
            )
            finish_reason = response.choices[0].finish_reason if response.choices else "none"
            content_text = response.choices[0].message.content if response.choices else None
            print(f"  finish_reason: {finish_reason}, chars: {len(content_text) if content_text else 0}")
            if content_text and content_text.strip():
                texto_limpio = content_text.strip()
                valido, razon = texto_es_valido(texto_limpio)
                if valido:
                    return texto_limpio
                print(f"  Texto invalido ({razon}), probando siguiente modelo...")
            else:
                print(f"  Modelo {modelo} devolvio texto vacio, probando siguiente...")
        except Exception as e:
            err = str(e)[:120]
            print(f"  Error con {modelo}: {err}")
            if "terms" in err.lower() or "terms acceptance" in err.lower():
                print(f"  -> Modelo requiere aceptar terminos, saltando...")
            # Try next model regardless

    raise Exception(f"No se pudo generar texto con ninguno de los modelos: {modelos_a_probar}")



ESCENAS_RELIGIOSAS = [
    # Naturaleza y luz divina
    "A person kneeling in prayer on a cliff overlooking a vast ocean at golden hour, rays of sunlight breaking through clouds, cinematic, photorealistic, 8k, dramatic lighting",
    "A lone figure standing in a field of wheat at sunrise, arms outstretched toward heaven, golden light flooding the scene, cinematic photography, award-winning",
    "Ancient stone church surrounded by cherry blossom trees in full bloom at dawn, soft pink and golden light, ethereal atmosphere, photorealistic 8k",
    "Silhouette of a person praying on a hilltop against a breathtaking sunset with purple and orange clouds, dramatic cinematic photography",
    "A wooden cross on a mountaintop at sunrise, rays of light emanating from behind it, fog in the valley below, epic landscape photography",
    "Hands holding an open Bible on a wooden table near a window with morning sunlight streaming in, dust particles in light, macro photography, warm tones",
    "A candle burning in a dark chapel with stained glass windows casting colorful light, intimate and peaceful, cinematic photography",
    "A white dove in flight against a golden sunset sky, wings spread wide, freedom and peace, stunning wildlife photography",
    "Ancient olive trees in a garden at dawn with soft mist, reminiscent of Gethsemane, atmospheric photography, peaceful",
    "A river flowing through a lush green valley with light breaking through storm clouds above, hope after rain, cinematic landscape",
    # Familia y comunidad
    "A family holding hands in prayer around a dinner table, warm candlelight, joy and gratitude on their faces, cinematic family photography",
    "An elderly woman with her hands clasped in prayer, face radiating peace and wisdom, close-up portrait, beautiful natural light",
    "A young child looking up at the sky in wonder, sunbeams falling on face, innocent and pure, golden hour portrait photography",
    "Two hands - one young, one elderly - clasped together in prayer, warm golden light, symbolic and moving, macro photography",
    "A group of people on a hilltop at sunset raising their hands in worship, silhouettes against fiery sky, powerful image",
    # Agua y naturaleza
    "Crystal clear mountain stream with light filtering through pine trees, peaceful and spiritual, nature photography, stunning colors",
    "A lighthouse on rocky cliffs during a dramatic storm, light cutting through darkness, symbolic of hope and guidance, epic photography",
    "A lone tree standing on a hill against a stormy sky with a rainbow breaking through, resilience and hope, landscape photography",
    "Sunbeams breaking through forest canopy onto a winding path, spiritual journey concept, dreamy atmospheric photography",
    "A still lake at dawn reflecting mountains and golden sky perfectly, tranquility and reflection, mirror-like surface",
    # Cielo y cosmos
    "The Milky Way galaxy above a small chapel in the mountains at night, stars filling the sky, cosmic and spiritual, long exposure photography",
    "Lightning storm over a desert landscape with a cross silhouette, power of God, dramatic photography, striking composition",
    "Aurora borealis (northern lights) in brilliant green and purple over a snowy landscape, divine beauty, stunning photography",
    "A full moon rising over a calm sea, golden path on water, peaceful and contemplative, night photography",
    "Dramatic cumulus clouds forming a cathedral-like arch in the sky, sun rays breaking through, epic sky photography",
    # SÃÂÃÂ­mbolos religiosos
    "An ornate golden cross in an ancient cathedral with light streaming through rose windows, sacred architecture, wide angle photography",
    "Open Bible on a rustic wooden surface with a small plant growing nearby, new life and scripture, still life photography",
    "A rosary laid on an old stone surface with a single flower, delicate and devotional, macro photography, warm tones",
    "Church bells silhouetted against a golden sunset sky, calling to prayer, atmospheric silhouette photography",
    "A simple wooden cross on a beach at low tide, reflection in wet sand, serene and powerful, minimalist photography"
]

def generar_prompt_imagen(pain_point):
    """Genera un prompt de imagen variado y cinematografico"""
    import random
    # Elegir escena aleatoria
    escena = random.choice(ESCENAS_RELIGIOSAS)
    return escena

def generar_imagen(image_prompt):
    """Genera imagen con Replicate usando REST API directamente (sin SDK)"""
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait=60"
    }
    payload = {
        "input": {
            "prompt": image_prompt,
            "num_outputs": 1,
            "output_format": "webp",
            "output_quality": 90,
            "width": 1080,
            "height": 1080
        }
    }
    print("  Enviando solicitud a Replicate...")
    r = requests.post(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        headers=headers,
        json=payload,
        timeout=120
    )
    if r.status_code not in (200, 201):
        raise Exception(f"Replicate HTTP {r.status_code}: {r.text}")

    result = r.json()
    max_attempts = 30
    attempt = 0
    while result.get("status") not in ("succeeded", "failed", "canceled") and attempt < max_attempts:
        pred_id = result.get("id")
        if not pred_id:
            raise Exception(f"Sin prediction ID: {result}")
        print(f"  Estado: {result.get('status')} - esperando...")
        time.sleep(3)
        poll = requests.get(
            f"https://api.replicate.com/v1/predictions/{pred_id}",
            headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            timeout=30
        )
        result = poll.json()
        attempt += 1

    if result.get("status") == "failed":
        raise Exception(f"Replicate fallo: {result.get('error')}")

    output = result.get("output")
    if not output:
        raise Exception(f"Sin output de Replicate: {result}")

    image_url = output[0] if isinstance(output, list) else str(output)
    print(f"  Imagen generada OK")
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()
    return resp.content, image_url


def publicar_con_foto(texto, image_data):
    """Publica texto + imagen en una sola llamada a /photos (mas simple, sin permisos extra)"""
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
    files = {"source": ("image.webp", image_data, "image/webp")}
    data = {
        "access_token": PAGE_ACCESS_TOKEN,
        "message": texto,
        "published": "true"
    }
    response = requests.post(url, files=files, data=data, timeout=60)
    return response.json()



def limpiar_para_voz(texto):
    import re
    t = texto
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'^#{1,6}\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'^>+\s*', '', t, flags=re.MULTILINE)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(r'[*_~`#>|\\]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def generar_voz(texto):
    """Genera audio natural dividiendo en frases y uniendo con ffmpeg.
    Cada frase se genera por separado para evitar cortes y pausas artificiales."""
    import re, random, subprocess, os, tempfile
    from gtts import gTTS

    CTAS = [
        "Síguenos para recibir más reflexiones como esta cada día.",
        "Si esto tocó tu corazón, dale me gusta y compártelo con alguien especial.",
        "Deja un amén en los comentarios si crees en el poder de Dios.",
        "Síguenos y recibe cada día una palabra de esperanza.",
        "Comenta lo que sientes. Tu testimonio puede cambiar la vida de alguien.",
        "Comparte esta reflexión. Tal vez alguien la necesita hoy.",
        "Dale me gusta si Dios ha sido fiel en tu vida.",
        "Síguenos para más mensajes de fe, esperanza y amor.",
        "Escribe amén si recibiste esta bendición en tu corazón.",
        "Comparte con tu familia. La fe se fortalece juntos.",
    ]

    texto_limpio = limpiar_para_voz(texto)

    # Cortar en punto final cerca del limite para no dejar frase incompleta
    limite = 650
    if len(texto_limpio) > limite:
        for sep in ['.', '!', '?', ',']:
            corte = texto_limpio.rfind(sep, 0, limite)
            if corte > 100:
                texto_limpio = texto_limpio[:corte + 1]
                break

    # Agregar CTA aleatorio
    cta = random.choice(CTAS)
    texto_final = texto_limpio.strip() + " " + cta
    print(f"  Texto para voz: {len(texto_final)} chars")
    print(f"  CTA: {cta}")

    # Dividir en frases por punto, signo de exclamacion o interrogacion
    # Mantener el signo al final de cada frase
    frases = re.split(r'(?<=[.!?])\s+', texto_final)
    frases = [f.strip() for f in frases if f.strip() and len(f.strip()) > 3]
    print(f"  Frases: {len(frases)}")

    if len(frases) <= 1:
        # Texto corto: generar de una sola vez
        tts = gTTS(text=texto_final, lang='es', slow=False)
        audio_path = '/tmp/audio_reflexion.mp3'
        tts.save(audio_path)
        with open(audio_path, 'rb') as f:
            return f.read()

    # Generar cada frase por separado y unir con ffmpeg
    archivos = []
    tmpdir = '/tmp/frases_audio'
    os.makedirs(tmpdir, exist_ok=True)

    for i, frase in enumerate(frases):
        path = f'{tmpdir}/frase_{i:02d}.mp3'
        try:
            tts = gTTS(text=frase, lang='es', slow=False)
            tts.save(path)
            archivos.append(path)
        except Exception as e:
            print(f"  Error en frase {i}: {e}")

    if not archivos:
        raise Exception("No se generaron frases de audio")

    if len(archivos) == 1:
        with open(archivos[0], 'rb') as f:
            return f.read()

    # Crear archivo de silencio de 0.25s entre frases
    silencio = f'{tmpdir}/silencio.mp3'
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i',
        'anullsrc=channel_layout=mono:sample_rate=24000',
        '-t', '0.25', '-q:a', '9', '-acodec', 'libmp3lame', silencio
    ], capture_output=True)

    # Construir lista de archivos para concatenar (frase, silencio, frase, silencio...)
    concat_list = f'{tmpdir}/concat.txt'
    with open(concat_list, 'w') as f:
        for j, arch in enumerate(archivos):
            f.write(f"file '{arch}'\n")
            if j < len(archivos) - 1:
                f.write(f"file '{silencio}'\n")

    output_path = '/tmp/audio_reflexion.mp3'
    result = subprocess.run([
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_list,
        '-acodec', 'libmp3lame', '-q:a', '4',
        output_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: usar solo la primera frase completa
        print(f"  ffmpeg concat error, usando frase completa: {result.stderr[-200:]}")
        tts = gTTS(text=texto_final[:400], lang='es', slow=False)
        tts.save(output_path)

    with open(output_path, 'rb') as f:
        data = f.read()
    print(f"  Audio final: {len(data)} bytes ({len(archivos)} frases)")
    return data

def crear_video(image_data, audio_data):
    """Combina imagen + audio con ffmpeg para crear video MP4"""
    import subprocess, json
    img_path = '/tmp/img_reflexion.webp'
    audio_path = '/tmp/audio_reflexion.mp3'
    output_path = '/tmp/video_reflexion.mp4'

    with open(img_path, 'wb') as f:
        f.write(image_data)
    with open(audio_path, 'wb') as f:
        f.write(audio_data)

    # Obtener duracion del audio
    duration = 30
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path],
            capture_output=True, text=True
        )
        info = json.loads(r.stdout)
        duration = float(info['format']['duration']) + 0.5
        print(f"  Duracion audio: {duration:.1f}s")
    except Exception as e:
        print(f"  No se pudo obtener duracion, usando 30s: {e}")

    # ffmpeg: imagen en loop + audio ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ video MP4 con fade in/out
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', img_path,
        '-i', audio_path,
        '-c:v', 'libx264', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-vf', f'scale=1080:1080,fade=t=in:st=0:d=0.5,fade=t=out:st={max(duration-1,duration-1):.1f}:d=0.5',
        '-shortest',
        '-t', str(duration),
        output_path
    ]
    print("  Creando video con ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffmpeg error: {result.stderr[-300:]}")

    with open(output_path, 'rb') as f:
        video_data = f.read()
    print(f"  Video creado: {len(video_data)} bytes ({duration:.1f}s)")
    return video_data


def publicar_video(texto, video_data):
    """Publica video en la pagina de Facebook"""
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/videos"
    files = {"source": ("video.mp4", video_data, "video/mp4")}
    data = {
        "access_token": PAGE_ACCESS_TOKEN,
        "description": texto,
        "published": "true"
    }
    print("  Subiendo video a Facebook (puede tardar)...")
    response = requests.post(url, files=files, data=data, timeout=180)
    return response.json()

def verificar_config():
    errores = []
    if not PAGE_ACCESS_TOKEN:
        errores.append("FACEBOOK_PAGE_ACCESS_TOKEN no configurado")
    if not GROQ_API_KEY:
        errores.append("GROQ_API_KEY no configurado")
    if not REPLICATE_API_TOKEN:
        errores.append("REPLICATE_API_TOKEN no configurado")
    if errores:
        for e in errores:
            print(f"ERROR: {e}")
        sys.exit(1)


def main():
    print(f"\n{'='*50}")
    print(f"Reflexiones Religiosas Bot")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    verificar_config()
    pain_point = seleccionar_pain_point()
    print(f"Tema: {pain_point['tema']}")
    print("Generando texto con Groq...")
    texto = generar_texto(pain_point)
    print(f"Texto generado: {len(texto)} caracteres")
    print(f"\n--- PREVIEW ---\n{texto[:150]}...\n")
    print("Generando imagen con Replicate...")
    image_data, image_url = generar_imagen(pain_point["prompt_imagen"])
    print(f"Imagen: {len(image_data)} bytes")
    # Alternar aleatoriamente: 50% foto, 50% video
    usar_video = random.random() < 0.5
    print(f"Modo: {'VIDEO ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¬' if usar_video else 'FOTO ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ·'}")

    if usar_video:
        print("Generando voz con gTTS...")
        audio_data = generar_voz(texto)
        print("Creando video con ffmpeg...")
        video_data = crear_video(image_data, audio_data)
        print(f"Video: {len(video_data)} bytes")
        result = publicar_video(texto, video_data)
        if "id" in result:
            print(f"\n{'='*50}")
            print(f"VIDEO PUBLICADO! ID: {result['id']}")
            print(f"{'='*50}\n")
        else:
            print(f"Error video Facebook: {result}")
            print("Intentando publicar como foto...")
            result = publicar_con_foto(texto, image_data)
            if "id" in result or "post_id" in result:
                post_id = result.get("id") or result.get("post_id")
                print(f"FOTO PUBLICADA como fallback! ID: {post_id}")
            else:
                print(f"Error Facebook: {result}")
                sys.exit(1)
    else:
        print("Publicando post con imagen en Facebook...")
        result = publicar_con_foto(texto, image_data)
        if "id" in result or "post_id" in result:
            post_id = result.get("id") or result.get("post_id")
            print(f"\n{'='*50}")
            print(f"FOTO PUBLICADA! ID: {post_id}")
            print(f"{'='*50}\n")
        else:
            print(f"Error Facebook: {result}")
            sys.exit(1)


if __name__ == "__main__":
    main()
