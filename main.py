import os
import requests
from urllib.parse import quote_plus
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ==========================================
#          CONFIGURACIÓN DE LA APP
# ==========================================

# Se crea una instancia de la aplicación FastAPI
app = FastAPI(title="Carros App")

# Se monta la carpeta /static para servir archivos como CSS o imágenes locales
app.mount("/static", StaticFiles(directory="."), name="static")


#                API KEYS

# Se obtienen las llaves desde variables de entorno (ideal para seguridad)
# Si no existen, se usan valores por defecto (solo para pruebas)
NINJAS_KEY = os.getenv("NINJAS_KEY") or "QDNSkaZN66xS1wxksueEBQ==0rN5eBfvlylc0nDC" #api kay para las especificaciones de carros
UNSPLASH_KEY = os.getenv("UNSPLASH_KEY") or "hUPKJUFTtAzaezVkaETf3PLL0OCY8zayPtEKQS1fId4" #api key para las imagenes
NEWS_KEY = os.getenv("NEWS_KEY") or "c2bd8d5d7c874abf909fef68f406ed74" #api key para las noticias

# Cabecera requerida por la API de API-Ninjas
HEADERS_NINJAS = {"X-Api-Key": NINJAS_KEY}

# Diccionario opcional para corregir marcas comunes
# por ejemplo "vw" debe ser "volkswagen"
MARCA_FIX = {
    "mercedes": "mercedes-benz",
    "vw": "volkswagen",
    "chevy": "chevrolet",
}



#        FUNCIÓN: Obtener información del carro

def obtener_info_auto(query: str):
    """
    Consulta la API de API-Ninjas para obtener las especificaciones
    de un vehículo según la marca o marca+modelo.
    """

    if not query:
        return []

    # Limpieza de la búsqueda
    query = query.strip().lower()

    # Si la búsqueda incluye modelo (ej: "toyota camry")
    if " " in query:
        make, model = query.split(" ", 1)
    else:
        make, model = query, ""

    # Fijar marcas alternativas (vw → volkswagen)
    make = MARCA_FIX.get(make, make)

    # Construcción del endpoint base para búsqueda
    url = f"https://api.api-ninjas.com/v1/cars?make={quote_plus(make)}"

    # Si el usuario también escribió un modelo, se agrega al URL
    if model:
        url += f"&model={quote_plus(model)}"

    try:
        # Petición GET a la API externa
        r = requests.get(url, headers=HEADERS_NINJAS, timeout=8)

        # Si hay error, se imprime en consola y se retorna vacío
        if r.status_code != 200:
            print(f"❌ Error API Ninjas: {r.status_code} {r.text}")
            return []

        # Retorna la lista de autos encontrados como JSON
        return r.json()

    except Exception as e:
        # Captura de errores como problemas de conexión
        print("❌ Error conexión API Ninjas:", e)
        return []


#        FUNCIÓN: Buscar imágenes en Unsplash

def buscar_imagenes(query: str):
    """Consulta imágenes relacionadas con el auto usando Unsplash."""
    if not query:
        return []

    # Se forma el término de búsqueda
    q = quote_plus(f"{query} car")

    url = f"https://api.unsplash.com/search/photos?query={q}&per_page=6&client_id={UNSPLASH_KEY}"

    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return []

        data = r.json().get("results", [])

        # Se retornan solo las URLs útiles
        return [{"url": i["urls"]["regular"], "desc": i.get("alt_description", "")} for i in data]

    except Exception:
        return []


#      FUNCIÓN: Buscar noticias del vehículo

def buscar_noticias(query: str):
    """Obtiene noticias recientes relacionadas con la marca o modelo."""
    if not query:
        return []

    q = quote_plus(query)
    url = f"https://newsapi.org/v2/everything?q={q}&language=es&pageSize=5&apiKey={NEWS_KEY}"

    try:
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return []

        data = r.json().get("articles", [])

        # Formato resumido de cada noticia
        return [{"title": a["title"], "url": a["url"], "source": a["source"]["name"]} for a in data]

    except Exception:
        return []


#      FUNCIÓN: Renderizar plantilla HTML

def render_base(content_html: str) -> HTMLResponse:
    """
    Inserta contenido dinámico dentro del template HTML principal.
    Permite mantener un diseño base reutilizable.
    """
    with open("templates.html", "r", encoding="utf-8") as f:
        base = f.read()
    return HTMLResponse(base.replace("{{content}}", content_html))



#RUTA PRINCIPAL

@app.get("/", response_class=HTMLResponse)
def index():
    """
    Página principal de la aplicación.
    Muestra un formulario de búsqueda.
    """

    content = """
    <section class="hero card">
      <h1>🚗 Carros App</h1>
      <p class="lead">Busca especificaciones técnicas, imágenes y noticias por marca o modelo.</p>

      <!-- Formulario que envía la marca o modelo al servidor -->
      <form action="/buscar" method="post" class="search-form">
        <input name="marca" type="text" placeholder="Ej: Toyota, Toyota Camry, Tesla Model 3" required />
        <button type="submit">Buscar</button>
      </form>

      <p class="hints">Prueba: <strong>Toyota</strong>, <strong>Camry</strong>, <strong>Tesla Model 3</strong></p>
    </section>
    """
    return render_base(content)


# RUTA DE BÚSQUEDA
@app.post("/buscar", response_class=HTMLResponse)
def buscar(marca: str = Form(...)):
    """
    Recibe la marca o modelo enviado desde el formulario,
    consulta APIs externas y muestra resultados en pantalla.
    """

    marca = marca.strip()

    # Llamadas a las funciones principales
    info = obtener_info_auto(marca)
    fotos = buscar_imagenes(marca)
    noticias = buscar_noticias(marca)

    # Botón volver
    html = f"<a class='back' href='/' target='_self'>← Volver</a>"

    # Título de resultados
    html += f"<h2>Resultados para <strong>{marca.title()}</strong></h2>"

  
    #     ESPECIFICACIONES
    if info:
        html += "<h3>Especificaciones</h3><div class='grid'>"

        for car in info:
            html += f"""
            <article class='card'>
              <h3>{car.get('make','')} {car.get('model','')} 
              <span class='muted'>({car.get('year','-')})</span></h3>

              <ul class='specs'>
                <li><strong>Clase:</strong> {car.get('class','-')}</li>
                <li><strong>Transmisión:</strong> {car.get('transmission','-')}</li>
                <li><strong>Tracción:</strong> {car.get('drive','-')}</li>
                <li><strong>Combustible:</strong> {car.get('fuel_type','-')}</li>
                <li><strong>Cilindros:</strong> {car.get('cylinders','-')}</li>
                <li><strong>Cilindraje:</strong> {car.get('displacement','-')}</li>
                <li><strong>City MPG:</strong> {car.get('city_mpg','-')}</li>
                <li><strong>Highway MPG:</strong> {car.get('highway_mpg','-')}</li>
                <li><strong>Combinado:</strong> {car.get('combination_mpg','-')}</li>
              </ul>
            </article>
            """

        html += "</div>"

    else:
        html += f"<p class='card'>⚠️ No se encontraron especificaciones para '{marca}'.</p>"

 
    #  IMÁGENES
    if fotos:
        html += "<h3>Imágenes</h3><div class='grid images'>"
        for f in fotos:
            html += f"""
            <div class='card'>
                <img src='{f['url']}' alt='{marca}' />
                <p class='caption'>{f['desc']}</p>
            </div>
            """
        html += "</div>"
    else:
        html += "<p class='card'>Sin imágenes disponibles.</p>"


    # NOTICIAS

    if noticias:
        html += "<h3>Noticias recientes</h3><div class='news-list'>"
        for n in noticias:
            html += f"""
            <div class='card news-item'>
                <a href='{n['url']}' target='_blank'>{n['title']}</a>
                <p class='muted'>{n['source']}</p>
            </div>
            """
        html += "</div>"
    else:
        html += "<p class='card'>No se encontraron noticias para esta búsqueda.</p>"

    return render_base(html)
