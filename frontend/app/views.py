from django.shortcuts import render, redirect
import requests
import xmltodict
import json
import plotly.graph_objects as go
import plotly.io as pio

contenido_archivo = ""

def index(request):
    global contenido_archivo

    if request.FILES:
        archivo = request.FILES['archivo']
        contenido_archivo = archivo.read().decode("utf-8")
        
        if contenido_archivo:
            try:
                # Convertir XML a JSON
                json_archivo = xmltodict.parse(contenido_archivo)

                # Enviar la solicitud POST a Flask
                response = requests.post("http://localhost:8001/cargarArchivo", json=json_archivo)

                # Verificar la respuesta
                if response.status_code == 200:
                    res = response.json()
                    mensaje = res.get("message", "")
                    resumen = res.get("resumen", {})
                    print("Resumen de carga:", resumen)

                    # Enviar el resumen al template
                    return render(request, "index.html", context={"contenido": contenido_archivo, "mensaje": mensaje, "resumen": resumen})
                else:
                    print(f"Error en la respuesta de carga: {response.status_code} - {response.text}")
                    return render(request, "index.html", context={"contenido": contenido_archivo, "mensaje": "Error al procesar el archivo."})
            except Exception as e:
                print(f"Error al procesar el archivo: {e}")
                return render(request, "index.html", context={"contenido": contenido_archivo, "mensaje": "Error en la conversión del archivo."})

    context = {"contenido": contenido_archivo}
    return render(request, "index.html", context=context)

def reset_api_view(request):
    global contenido_archivo

    if request.method == 'POST':
        api_url = 'http://localhost:8001/reset'
        
        try:
            response = requests.post(api_url)
            if response.status_code == 200:
                contenido_archivo = ""
                mensaje = "La base de datos se ha restablecido exitosamente."
                return render(request, "index.html", context={"mensaje": mensaje})
            else:
                print(f"Error en la respuesta al restablecer: {response.status_code} - {response.text}")
                return render(request, "index.html", context={"mensaje": "Error al restablecer la base de datos."})
        except requests.exceptions.RequestException as e:
            print("Error de conexión al restablecer:", e)
            return render(request, "index.html", context={"mensaje": f"Error al comunicarse con la API: {e}"})
    
    return render(request, "index.html")

def consultar_datos(request):
    global contenido_archivo

    # Verificar si se ha cargado un archivo
    if not contenido_archivo:
        return render(request, "peticiones.html", context={"mensaje_error": "Cargue un archivo primero"})

    try:
        response = requests.get("http://localhost:8001/consultarDatos")
        
        if response.status_code == 200:
            datos_xml = response.text
            print("Respuesta XML obtenida de consultarDatos:", datos_xml)
            return render(request, "peticiones.html", context={"datos_xml": datos_xml})
        else:
            print(f"Error en la respuesta de consultar datos: {response.status_code} - {response.text}")
            return render(request, "peticiones.html", context={"mensaje_error": "Error al consultar datos"})
    except requests.exceptions.RequestException as e:
        print("Error de conexión al consultar datos:", e)
        return render(request, "peticiones.html", context={"mensaje_error": f"Error al comunicarse con la API: {e}"})

def ayuda(request):
    return render(request, 'ayuda.html')

def peticiones(request):
    return render(request, 'peticiones.html') 

def analizar_mensaje_prueba(request):
    """
    Permite enviar un mensaje en formato XML al backend en Flask para su análisis de sentimientos,
    y muestra la respuesta en la página.
    """
    if request.method == "POST":
        mensaje = request.POST.get("mensaje", "")
        
        # Enviar el mensaje al backend en Flask
        try:
            headers = {'Content-Type': 'application/xml'}
            response = requests.post("http://localhost:8001/analizarMensajePrueba", data=mensaje.encode('utf-8'), headers=headers)

            if response.status_code == 200:
                # Almacena la respuesta para mostrarla en el área de texto de respuesta
                datos_respuesta = response.text
                return render(request, "peticiones.html", context={"datos_respuesta": datos_respuesta})
            else:
                mensaje_error = "Error al procesar el mensaje de prueba. Intente de nuevo."
                return render(request, "peticiones.html", context={"mensaje_error": mensaje_error})
        except requests.exceptions.RequestException as e:
            mensaje_error = f"Error al comunicarse con el API: {e}"
            return render(request, "peticiones.html", context={"mensaje_error": mensaje_error})

    return render(request, "peticiones.html")  
def resumen_clasificacion_por_fecha(request):
    """
    Función para obtener el resumen de clasificación por fecha y renderizar la gráfica.
    """
    graph_html = None  # Inicializar variable para la gráfica

    if request.method == "POST":
        fecha = request.POST.get("fecha")
        empresa = request.POST.get("empresa", "").lower()

        # Solicitar datos al backend de Flask
        response = requests.get(f"http://localhost:8001/resumen_clasificacion_por_fecha?fecha={fecha}&empresa={empresa}")
        
        if response.status_code == 200:
            datos_resumen = response.json()
            resumen = datos_resumen['resumen']

            # Crear la gráfica con Plotly
            fig = go.Figure(data=[
                go.Bar(name='Total', x=['Mensajes'], y=[resumen['total']]),
                go.Bar(name='Positivos', x=['Mensajes'], y=[resumen['positivos']]),
                go.Bar(name='Negativos', x=['Mensajes'], y=[resumen['negativos']]),
                go.Bar(name='Neutros', x=['Mensajes'], y=[resumen['neutros']])
            ])

            # Personalizar la gráfica
            fig.update_layout(
                title=f"Resumen de clasificación para {datos_resumen['empresa']} en la fecha {datos_resumen['fecha']}",
                barmode='group'
            )

            # Convertir la gráfica a HTML
            graph_html = pio.to_html(fig, full_html=False)

        else:
            return render(request, "resumen.html", context={"mensaje_error": "Error al obtener el resumen."})

    return render(request, "resumen.html", context={"graph_html": graph_html})



