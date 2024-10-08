from flask import Flask, request, jsonify, Response
import dicttoxml
import re
from tda import ListaEnlazada
import xmltodict
from datetime import datetime

app = Flask(__name__)

# Crear una instancia global de la lista enlazada
mensajes = ListaEnlazada()
resumen_global = {"total": 0, "positivos": 0, "negativos": 0, "neutros": 0}
analisis_empresas = {}
fecha_entrada = None  # Variable para almacenar la fecha del primer mensaje procesado

@app.route("/cargarArchivo", methods=["POST"])
def cargar_archivo():
    global mensajes, resumen_global, analisis_empresas, fecha_entrada  # Usar las variables globales

    # Reiniciar los contadores, análisis de empresas y fecha de entrada
    resumen_global = {"total": 0, "positivos": 0, "negativos": 0, "neutros": 0}
    analisis_empresas = {}
    fecha_entrada = None

    body = request.json

    if not body:
        return jsonify({"error": "No JSON received"}), 400

    try:
        diccionario = body.get("solicitud_clasificacion", {}).get("diccionario", {})
        sentimientos_positivos = diccionario.get("sentimientos_positivos", {}).get("palabra", [])
        sentimientos_negativos = diccionario.get("sentimientos_negativos", {}).get("palabra", [])
        empresas_analizar = diccionario.get("empresas_analizar", {}).get("empresa", [])

        if isinstance(empresas_analizar, dict):
            empresas_analizar = [empresas_analizar]

        lista_mensajes = body.get("solicitud_clasificacion", {}).get("lista_mensajes", {}).get("mensaje", [])

        for mensaje in lista_mensajes:
            datos = extraer_datos_mensaje(mensaje)

            # Capturar la fecha del primer mensaje si aún no está establecida
            if not fecha_entrada and datos["fecha"]:
                fecha_entrada = datos["fecha"].split()[0]  # Guardar solo la fecha sin hora

            clasificacion = clasificar_mensaje(mensaje, sentimientos_positivos, sentimientos_negativos)

            # Agregar el mensaje a la lista enlazada
            mensajes.agregar({"mensaje": datos, "clasificacion": clasificacion})

            # Contabilizar el resumen general
            resumen_global["total"] += 1
            if clasificacion == "positivo":
                resumen_global["positivos"] += 1
            elif clasificacion == "negativo":
                resumen_global["negativos"] += 1
            else:
                resumen_global["neutros"] += 1

            # Análisis por empresa y servicios
            for empresa in empresas_analizar:
                nombre_empresa = empresa.get("nombre", "").lower()
                servicios = empresa.get("servicios", {}).get("servicio", [])

                if isinstance(servicios, dict):
                    servicios = [servicios]

                if nombre_empresa not in analisis_empresas:
                    analisis_empresas[nombre_empresa] = {
                        "total": 0, "positivos": 0, "negativos": 0, "neutros": 0, "servicios": {}
                    }

                # Verificar si la empresa está mencionada en el mensaje
                empresa_mencionada = re.search(r'\b' + re.escape(nombre_empresa) + r'\b', mensaje, re.IGNORECASE) is not None

                for servicio in servicios:
                    nombre_servicio = servicio.get("@nombre", "").lower()
                    alias_servicio = procesar_alias(servicio.get("alias", []))

                    if isinstance(alias_servicio, str):
                        alias_servicio = [alias_servicio]

                    # Verificar si el servicio está mencionado
                    servicio_mencionado = any(
                        re.search(r'\b' + re.escape(alias.lower()) + r'\b', mensaje, re.IGNORECASE) for alias in alias_servicio
                    ) or re.search(r'\b' + re.escape(nombre_servicio) + r'\b', mensaje, re.IGNORECASE)

                    if servicio_mencionado:
                        if nombre_servicio not in analisis_empresas[nombre_empresa]["servicios"]:
                            analisis_empresas[nombre_empresa]["servicios"][nombre_servicio] = {
                                "total": 0, "positivos": 0, "negativos": 0, "neutros": 0
                            }

                        analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["total"] += 1
                        if clasificacion == "positivo":
                            analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["positivos"] += 1
                        elif clasificacion == "negativo":
                            analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["negativos"] += 1
                        else:
                            analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["neutros"] += 1

                if empresa_mencionada:
                    analisis_empresas[nombre_empresa]["total"] += 1
                    if clasificacion == "positivo":
                        analisis_empresas[nombre_empresa]["positivos"] += 1
                    elif clasificacion == "negativo":
                        analisis_empresas[nombre_empresa]["negativos"] += 1
                    else:
                        analisis_empresas[nombre_empresa]["neutros"] += 1

        # Generar XML solo si hay mensajes procesados
        if resumen_global["total"] > 0:
            xml = dicttoxml.dicttoxml(mensajes.recorrer(), attr_type=False)
            print(xml)

        # Resumen para la respuesta
        resumen = {
            "total_mensajes": resumen_global["total"],
            "positivos": resumen_global["positivos"],
            "negativos": resumen_global["negativos"],
            "neutros": resumen_global["neutros"],
            "analisis_empresas": analisis_empresas
        }

        return jsonify({"message": "Se cargó con éxito.", "resumen": resumen}), 200

    except KeyError as e:
        return jsonify({"error": f"Missing key: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reset", methods=["POST"])
def reset():
    global mensajes  # Usar la instancia global
    mensajes = ListaEnlazada()  # Reiniciar la lista enlazada
    return jsonify({"message": "La base de datos se ha restablecido exitosamente."}), 200

@app.route("/consultarDatos", methods=["GET"])
def consultar_datos():
    # Crear la estructura XML personalizada, usando la fecha del archivo de entrada
    fecha_respuesta = fecha_entrada or "Fecha no disponible"
    response_data = {
        "lista_respuestas": {
            "respuesta": {
                "fecha": fecha_respuesta,
                "mensajes": {
                    "total": resumen_global["total"],
                    "positivos": resumen_global["positivos"],
                    "negativos": resumen_global["negativos"],
                    "neutros": resumen_global["neutros"]
                },
                "analisis": {
                    "empresa": []
                }
            }
        }
    }

    for nombre_empresa, datos in analisis_empresas.items():
        empresa_data = {
            "nombre": nombre_empresa,
            "mensajes": {
                "total": datos["total"],
                "positivos": datos["positivos"],
                "negativos": datos["negativos"],
                "neutros": datos["neutros"]
            },
            "servicios": {
                "servicio": []
            }
        }

        for nombre_servicio, detalles in datos["servicios"].items():
            servicio_data = {
                "nombre": nombre_servicio,
                "mensajes": {
                    "total": detalles["total"],
                    "positivos": detalles["positivos"],
                    "negativos": detalles["negativos"],
                    "neutros": detalles["neutros"]
                }
            }
            empresa_data["servicios"]["servicio"].append(servicio_data)

        response_data["lista_respuestas"]["respuesta"]["analisis"]["empresa"].append(empresa_data)

    datos_xml = dicttoxml.dicttoxml(response_data, custom_root="lista_respuestas", attr_type=False)
    return Response(datos_xml, mimetype="application/xml")

def clasificar_mensaje(mensaje, sentimientos_positivos, sentimientos_negativos):
    mensaje_palabras = mensaje.lower().split()
    sentimientos_positivos = [palabra.lower() for palabra in sentimientos_positivos if isinstance(palabra, str)]
    sentimientos_negativos = [palabra.lower() for palabra in sentimientos_negativos if isinstance(palabra, str)]

    positivos = sum(1 for palabra in mensaje_palabras if palabra in sentimientos_positivos)
    negativos = sum(1 for palabra in mensaje_palabras if palabra in sentimientos_negativos)

    return "positivo" if positivos > negativos else "negativo" if negativos > positivos else "neutro"

def procesar_alias(alias_servicio):
    return list(set(alias_servicio)) if isinstance(alias_servicio, list) else alias_servicio

def extraer_datos_mensaje(mensaje):
    """Extrae los datos clave de un mensaje usando expresiones regulares."""
    fecha = re.search(r"\b\d{2}/\d{2}/\d{4} \d{2}:\d{2}\b", mensaje)
    lugar = re.search(r"Lugar y fecha: (.*?),", mensaje)
    usuario = re.search(r"Usuario:\s*([^\s]+)", mensaje)
    red_social = re.search(r"Red social:\s*([^\s]+)", mensaje)

    return {
        "fecha": fecha.group(0) if fecha else "",
        "lugar": lugar.group(1) if lugar else "",
        "usuario": usuario.group(1) if usuario else "",
        "red_social": red_social.group(1) if red_social else ""
    }

if __name__ == "__main__":
    app.run(debug=True, port=8001)
