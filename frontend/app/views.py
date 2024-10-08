from django.shortcuts import render
import requests
import xmltodict
import re

contenido_archivo = ""

# Create your views here.
def index(request):
    global contenido_archivo

    if request.FILES:
        archivo = request.FILES['archivo']
        contenido_archivo = archivo.read().decode("utf-8")
        if contenido_archivo != "":
            json_archivo = xmltodict.parse(contenido_archivo)
            response = requests.post("http://localhost:8001/cargarArchivo", json=json_archivo)
            res = response.json()
            print(res["message"])
    
    context={"contenido": contenido_archivo}
    return render(request, "index.html",context=context)

def about(request):
    response = requests.get("http://localhost:8001/obtenerArchivo")
    res = response.json()
    print(res['pizzas'])
    return render(request, "about.html")