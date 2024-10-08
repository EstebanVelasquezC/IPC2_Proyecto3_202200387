from django.shortcuts import render, redirect
import requests
import xmltodict
import json

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
