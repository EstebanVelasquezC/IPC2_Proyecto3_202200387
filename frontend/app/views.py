# archivo views.py
from django.shortcuts import render
import requests
import xmltodict

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
                    print(resumen)  # Mostrar el resumen en la terminal

                    # Enviar el resumen al template
                    return render(request, "index.html", context={"contenido": contenido_archivo, "mensaje": mensaje, "resumen": resumen})
                else:
                    print(f"Error en la respuesta: {response.text}")
                    return render(request, "index.html", context={"contenido": contenido_archivo, "mensaje": "Error al procesar el archivo."})
            except Exception as e:
                print(f"Error al procesar el archivo: {e}")
                return render(request, "index.html", context={"contenido": contenido_archivo, "mensaje": "Error en la conversión del archivo."})

    context = {"contenido": contenido_archivo}
    return render(request, "index.html", context=context)

def about(request):
    return render(request, 'about.html')

