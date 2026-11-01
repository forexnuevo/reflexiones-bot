#!/usr/bin/env python3
"""
Generador automatico de posts para Facebook - Reflexiones Religiosas
Usa Groq (GRATIS) para texto + Replicate para imagenes + Facebook Graph API para publicar
"""

import os
import random
import requests
import json
import sys
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("Instalando openai...")
    os.system("pip install openai --quiet")
    from openai import OpenAI

try:
    import replicate
except ImportError:
    print("Instalando replicate...")
    os.system("pip install replicate --quiet")
    import replicate

# ============================================================
# CONFIGURACION
# ============================================================
PAGE_ID = "102300045081467"
PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

# ============================================================
# PAIN POINTS - Los 5 temas que mas mueven al publico religioso
# ============================================================
PAIN_POINTS = [
    {
        "tema": "soledad",
        "peso": 25,
        "prompt_texto": """Escribe una publicacion emotiva para Facebook sobre sentirse solo y encontrar consuelo en Dios.
Estructura OBLIGATORIA:
1. Primera linea que GOLPEE el corazon (ej: "Sientes que nadie te entiende?" o "Hoy me senti completamente solo...")
2. Parrafo de empatia reconociendo el dolor (2-3 oraciones)
3. Un versiculo biblico consolador (con referencia)
4. Una oracion corta y poderosa al Senor
5. Call to action: "Escribe AMEN si sientes que Dios esta contigo" o similar
NO uses hashtags. Tono: intimo, conversacional, emotivo. Maximo 280 palabras. En espanol.""",
        "prompt_imagen": "peaceful divine golden light rays shining through dark forest clearing, person kneeling in prayer silhouette, warm and ethereal atmosphere, spiritual hope, photorealistic"
    },
    {
        "tema": "familia_en_crisis",
        "peso": 25,
        "prompt_texto": """Escribe una publicacion poderosa para Facebook sobre familias que estan pasando por crisis, conflictos o separaciones.
Estructura OBLIGATORIA:
1. Primera linea que toque a quien tiene problemas familiares (ej: "Tu familia esta pasando por un momento dificil?")
2. Parrafo validando el dolor familiar (2-3 oraciones)
3. Un versiculo biblico sobre restauracion familiar
4. Una oracion de unidad y restauracion
5. Call to action: "Tienes alguien de tu familia que necesita esta oracion? Etiquetalao aqui abajo"
NO uses hashtags. Tono: esperanzador, familiar. Maximo 280 palabras. En espanol.""",
        "prompt_imagen": "family silhouette at golden sunset, parents and children holding hands, warm orange and purple sky, unity and love, heartwarming scene, photorealistic"
    },
    {
        "tema": "dificultades_economicas",
        "peso": 20,
        "prompt_texto": """Escribe una publicacion inspiradora para Facebook para personas con problemas economicos, deudas o desempleo.
Estructura OBLIGATORIA:
1. Primera linea que resuene con alguien en crisis economica
2. Parrafo de empatia con la angustia economica (2-3 oraciones)
3. Versiculo biblico sobre provision divina (Filipenses 4:19 o similar)
4. Oracion de fe declarando provision
5. Call to action: "Escribe SENOR PROVERAS si confias en que Dios tiene un milagro para ti"
NO uses hashtags. Tono: esperanzador, de fe. Maximo 280 palabras. En espanol.""",
        "prompt_imagen": "hands open receiving divine golden light from above, warm golden coins of light, abundance and blessing, peaceful and hopeful, spiritual provision concept, photorealistic"
    },
    {
        "tema": "duelo_y_perdida",
        "peso": 15,
        "prompt_texto": """Escribe una publicacion consoladora para Facebook para personas que han perdido a un ser querido o estan en duelo.
Estructura OBLIGATORIA:
1. Primera linea que abrace el corazon de quien llora
2. Parrafo de consuelo genuino (2-3 oraciones)
3. Versiculo sobre vida eterna y esperanza (Juan 11:25 o similar)
4. Oracion por quienes estan en duelo
5. Call to action: "Comparte esto con alguien que necesite saber que no esta solo en su dolor"
NO uses hashtags. Tono: suave, consolador, tierno. Maximo 280 palabras. En espanol.""",
        "prompt_imagen": "white dove flying into bright heavenly light, peaceful memorial candle, soft flowers, sunrise breaking through gentle clouds, hope and eternal life, photorealistic"
    },
    {
        "tema": "abandono_espiritual",
        "peso": 15,
        "prompt_texto": """Escribe una publicacion poderosa para Facebook sobre el sentimiento de que Dios esta lejos o ausente en tiempos dificiles.
Estructura OBLIGATORIA:
1. Primera linea que valide ese sentimiento de silencio de Dios
2. Parrafo validando la lucha espiritual (2-3 oraciones)
3. Versiculo que confirme la presencia constante de Dios (Isaias 41:10 o similar)
4. Declaracion de fe y oracion
5. Call to action: "Escribe CONFIO EN TI SENOR si hoy eliges creer aunque no sientes"
NO uses hashtags. Tono: honesto, poderoso, de fe madura. Maximo 280 palabras. En espanol.""",
        "prompt_imagen": "person standing alone in dark valley looking up at single powerful beam of divine light breaking through dramatic storm clouds, spiritual awakening, hope in darkness, photorealistic"
    }
]


def seleccionar_pain_point():
    temas = [p["tema"] for p in PAIN_POINTS]
    pesos = [p["peso"] for p in PAIN_POINTS]
    tema_elegido = random.choices(temas, weights=pesos, k=1)[0]
    return next(p for p in PAIN_POINTS if p["tema"] == tema_elegido)


def generar_texto(pain_point):
    """Genera el texto del post con Groq (GRATIS)"""
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un escritor espiritual experto en contenido de Facebook para paginas religiosas hispanas. "
                    "Tu objetivo es crear publicaciones autenticas y emotivas que generen AMEN, comentarios y compartidos. "
                    "El contenido debe tocar los dolores reales del publico cristiano de habla hispana. "
                    "Escribe como alguien que genuinamente ha pasado por esos momentos, no como un pastor dando un sermon. "
                    "IMPORTANTE: Nunca uses hashtags. El formato debe ser parrafos naturales."
                )
            },
            {"role": "user", "content": pain_point["prompt_texto"]}
        ],
        max_tokens=700,
        temperature=0.85
    )
    return response.choices[0].message.content.strip()


def generar_imagen(image_prompt):
    """Genera imagen con Replicate usando flux-schnell"""
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={
            "prompt": image_prompt,
            "num_outputs": 1,
            "output_format": "webp",
            "output_quality": 90,
            "width": 1080,
            "height": 1080
        }
    )
    image_url = str(output[0])
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    return response.content, image_url


def subir_imagen_facebook(image_data):
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"
    files = {'source': ('image.webp', image_data, 'image/webp')}
    data = {'access_token': PAGE_ACCESS_TOKEN, 'published': 'false'}
    response = requests.post(url, files=files, data=data, timeout=60)
    result = response.json()
    if 'id' in result:
        return result['id']
    else:
        raise Exception(f"Error subiendo imagen: {result}")


def publicar_post(texto, photo_id=None):
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
    data = {'message': texto, 'access_token': PAGE_ACCESS_TOKEN}
    if photo_id:
        data['attached_media'] = json.dumps([{'media_fbid': photo_id}])
    response = requests.post(url, data=data, timeout=30)
    return response.json()


def verificar_config():
    errores = []
    if not PAGE_ACCESS_TOKEN:
        errores.append("FACEBOOK_PAGE_ACCESS_TOKEN no esta configurado")
    if not GROQ_API_KEY:
        errores.append("GROQ_API_KEY no esta configurado")
    if not REPLICATE_API_TOKEN:
        errores.append("REPLICATE_API_TOKEN no esta configurado")
    if errores:
        print("ERROR - Variables de entorno faltantes:")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)


def main():
    print(f"\n{'='*50}")
    print(f"Reflexiones Religiosas Bot")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")
    verificar_config()
    pain_point = seleccionar_pain_point()
    print(f"Tema seleccionado: {pain_point['tema']}")
    print("Generando texto con Groq (gratis)...")
    texto = generar_texto(pain_point)
    print(f"Texto generado ({len(texto)} caracteres)")
    print(f"\n--- PREVIEW ---\n{texto[:200]}...\n")
    print("Generando imagen con Replicate...")
    image_data, image_url = generar_imagen(pain_point["prompt_imagen"])
    print(f"Imagen generada: {image_url}")
    print("Subiendo imagen a Facebook...")
    photo_id = subir_imagen_facebook(image_data)
    print(f"Imagen subida, ID: {photo_id}")
    print("Publicando post en Facebook...")
    result = publicar_post(texto, photo_id)
    if 'id' in result:
        post_id = result['id']
        print(f"\nPOST PUBLICADO EXITOSAMENTE!")
        print(f"Post ID: {post_id}")
    else:
        print(f"\nError publicando post: {result}")
        sys.exit(1)
    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    main()
