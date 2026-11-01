#!/usr/bin/env python3
"""
Generador automático de posts para Facebook - Reflexiones Religiosas
Usa OpenAI para texto + Replicate para imágenes + Facebook Graph API para publicar
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
# CONFIGURACIÓN
# ============================================================
PAGE_ID = "102300045081467"
PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

# ============================================================
# PAIN POINTS - Los 5 temas que más mueven al público religioso
# ============================================================
PAIN_POINTS = [
    {
        "tema": "soledad",
        "peso": 25,  # Porcentaje de frecuencia
        "prompt_texto": """Escribe una publicación emotiva para Facebook sobre sentirse solo y encontrar consuelo en Dios.
Estructura OBLIGATORIA:
1. Primera línea que GOLPEE el corazón (ej: "¿Sientes que nadie te entiende?" o "Hoy me sentí completamente solo...")
2. Párrafo de empatía reconociendo el dolor (2-3 oraciones)
3. Un versículo bíblico consolador (con referencia)
4. Una oración corta y poderosa al Señor
5. Call to action: "Escribe AMÉN si sientes que Dios está contigo" o similar
NO uses hashtags. Tono: íntimo, conversacional, emotivo. Máximo 280 palabras. En español.""",
        "prompt_imagen": "peaceful divine golden light rays shining through dark forest clearing, person kneeling in prayer silhouette, warm and ethereal atmosphere, spiritual hope, photorealistic"
    },
    {
        "tema": "familia_en_crisis",
        "peso": 25,
        "prompt_texto": """Escribe una publicación poderosa para Facebook sobre familias que están pasando por crisis, conflictos o separaciones.
Estructura OBLIGATORIA:
1. Primera línea que toque a quien tiene problemas familiares (ej: "¿Tu familia está pasando por un momento difícil?")
2. Párrafo validando el dolor familiar (2-3 oraciones)
3. Un versículo bíblico sobre restauración familiar
4. Una oración de unidad y restauración
5. Call to action: "¿Tienes alguien de tu familia que necesita esta oración? Etiquétalo aquí abajo 👇"
NO uses hashtags. Tono: esperanzador, familiar. Máximo 280 palabras. En español.""",
        "prompt_imagen": "family silhouette at golden sunset, parents and children holding hands, warm orange and purple sky, unity and love, heartwarming scene, photorealistic"
    },
    {
        "tema": "dificultades_economicas",
        "peso": 20,
        "prompt_texto": """Escribe una publicación inspiradora para Facebook para personas con problemas económicos, deudas o desempleo.
Estructura OBLIGATORIA:
1. Primera línea que resuene con alguien en crisis económica (ej: "¿Las deudas no te dejan dormir?" o "A veces me pregunto cómo voy a llegar a fin de mes...")
2. Párrafo de empatía con la angustia económica (2-3 oraciones)
3. Versículo bíblico sobre provisión divina (Filipenses 4:19 o similar)
4. Oración de fe declarando provisión
5. Call to action: "Escribe SEÑOR PROVEERÁS si confías en que Dios tiene un milagro para ti"
NO uses hashtags. Tono: esperanzador, de fe. Máximo 280 palabras. En español.""",
        "prompt_imagen": "hands open receiving divine golden light from above, warm golden coins of light, abundance and blessing, peaceful and hopeful, spiritual provision concept, photorealistic"
    },
    {
        "tema": "duelo_y_perdida",
        "peso": 15,
        "prompt_texto": """Escribe una publicación consoladora para Facebook para personas que han perdido a un ser querido o están en duelo.
Estructura OBLIGATORIA:
1. Primera línea que abrace el corazón de quien llora (ej: "Para quien ha perdido a alguien que amaba..." o "La muerte de un ser querido es un dolor que solo Dios puede sanar...")
2. Párrafo de consuelo genuino (2-3 oraciones)
3. Versículo sobre vida eterna y esperanza (Juan 11:25 o similar)
4. Oración por quienes están en duelo
5. Call to action: "Comparte esto con alguien que necesite saber que no está solo en su dolor"
NO uses hashtags. Tono: suave, consolador, tierno. Máximo 280 palabras. En español.""",
        "prompt_imagen": "white dove flying into bright heavenly light, peaceful memorial candle, soft flowers, sunrise breaking through gentle clouds, hope and eternal life, photorealistic"
    },
    {
        "tema": "abandono_espiritual",
        "peso": 15,
        "prompt_texto": """Escribe una publicación poderosa para Facebook sobre el sentimiento de que Dios está lejos o ausente en tiempos difíciles.
Estructura OBLIGATORIA:
1. Primera línea que valide ese sentimiento de silencio de Dios (ej: "¿Alguna vez has orado y sentido que Dios no te escucha?" o "Hay noches donde el cielo parece de hierro...")
2. Párrafo validando la lucha espiritual (2-3 oraciones)
3. Versículo que confirme la presencia constante de Dios (Isaías 41:10 o similar)
4. Declaración de fe y oración
5. Call to action: "Escribe CONFÍO EN TI SEÑOR si hoy eliges creer aunque no sientes"
NO uses hashtags. Tono: honesto, poderoso, de fe madura. Máximo 280 palabras. En español.""",
        "prompt_imagen": "person standing alone in dark valley looking up at single powerful beam of divine light breaking through dramatic storm clouds, spiritual awakening, hope in darkness, photorealistic"
    }
]


def seleccionar_pain_point():
    """Selecciona un pain point según sus pesos"""
    temas = [p["tema"] for p in PAIN_POINTS]
    pesos = [p["peso"] for p in PAIN_POINTS]
    tema_elegido = random.choices(temas, weights=pesos, k=1)[0]
    return next(p for p in PAIN_POINTS if p["tema"] == tema_elegido)


def generar_texto(pain_point):
    """Genera el texto del post con OpenAI"""
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un escritor espiritual experto en contenido de Facebook para páginas religiosas hispanas. "
                    "Tu objetivo es crear publicaciones auténticas y emotivas que generen AMÉN, comentarios y compartidos. "
                    "El contenido debe tocar los dolores reales del público cristiano de habla hispana. "
                    "Escribe como alguien que genuinamente ha pasado por esos momentos, no como un pastor dando un sermón. "
                    "IMPORTANTE: Nunca uses hashtags. El formato debe ser párrafos naturales."
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

    # Descargar la imagen
    image_url = str(output[0])
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    return response.content, image_url


def subir_imagen_facebook(image_data):
    """Sube la imagen a Facebook sin publicarla (unpublished)"""
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/photos"

    files = {
        'source': ('image.webp', image_data, 'image/webp')
    }
    data = {
        'access_token': PAGE_ACCESS_TOKEN,
        'published': 'false'
    }

    response = requests.post(url, files=files, data=data, timeout=60)
    result = response.json()

    if 'id' in result:
        return result['id']
    else:
        raise Exception(f"Error subiendo imagen: {result}")


def publicar_post(texto, photo_id=None):
    """Publica el post en la página de Facebook"""
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"

    data = {
        'message': texto,
        'access_token': PAGE_ACCESS_TOKEN
    }

    if photo_id:
        data['attached_media'] = json.dumps([{'media_fbid': photo_id}])

    response = requests.post(url, data=data, timeout=30)
    result = response.json()

    return result


def verificar_config():
    """Verifica que todas las variables de entorno estén configuradas"""
    errores = []
    if not PAGE_ACCESS_TOKEN:
        errores.append("FACEBOOK_PAGE_ACCESS_TOKEN no está configurado")
    if not OPENAI_API_KEY:
        errores.append("OPENAI_API_KEY no está configurado")
    if not REPLICATE_API_TOKEN:
        errores.append("REPLICATE_API_TOKEN no está configurado")

    if errores:
        print("❌ ERROR - Variables de entorno faltantes:")
        for e in errores:
            print(f"  - {e}")
        sys.exit(1)


def main():
    print(f"\n{'='*50}")
    print(f"🙏 Reflexiones Religiosas Bot")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # Verificar configuración
    verificar_config()

    # Seleccionar pain point
    pain_point = seleccionar_pain_point()
    print(f"🎯 Tema seleccionado: {pain_point['tema']}")

    # Generar texto
    print("✍️  Generando texto con OpenAI...")
    texto = generar_texto(pain_point)
    print(f"✅ Texto generado ({len(texto)} caracteres)")
    print(f"\n--- PREVIEW ---\n{texto[:200]}...\n")

    # Generar imagen
    print("🎨 Generando imagen con Replicate...")
    image_data, image_url = generar_imagen(pain_point["prompt_imagen"])
    print(f"✅ Imagen generada: {image_url}")

    # Subir imagen a Facebook
    print("📤 Subiendo imagen a Facebook...")
    photo_id = subir_imagen_facebook(image_data)
    print(f"✅ Imagen subida, ID: {photo_id}")

    # Publicar post
    print("📢 Publicando post en Facebook...")
    result = publicar_post(texto, photo_id)

    if 'id' in result:
        post_id = result['id']
        print(f"\n✅ POST PUBLICADO EXITOSAMENTE!")
        print(f"📌 Post ID: {post_id}")
        print(f"🔗 Ver en: https://www.facebook.com/{post_id.replace('_', '/posts/')}")
    else:
        print(f"\n❌ Error publicando post: {result}")
        sys.exit(1)

    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    main()
