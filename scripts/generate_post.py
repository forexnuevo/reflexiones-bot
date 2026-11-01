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
                return content_text.strip()
            print(f"  Modelo {modelo} devolvio texto vacio, probando siguiente...")
        except Exception as e:
            err = str(e)[:120]
            print(f"  Error con {modelo}: {err}")
            if "terms" in err.lower() or "terms acceptance" in err.lower():
                print(f"  -> Modelo requiere aceptar terminos, saltando...")
            # Try next model regardless

    raise Exception(f"No se pudo generar texto con ninguno de los modelos: {modelos_a_probar}")


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
    print("Publicando post con imagen en Facebook...")
    result = publicar_con_foto(texto, image_data)
    if "id" in result or "post_id" in result:
        post_id = result.get("id") or result.get("post_id")
        print(f"\n{'='*50}")
        print(f"POST PUBLICADO! ID: {post_id}")
        print(f"{'='*50}\n")
    else:
        print(f"Error Facebook: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()
