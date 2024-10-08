from flask import Flask, request, jsonify, Response
import dicttoxml
import re
from tda import ListaEnlazada
import xmltodict
from datetime import datetime
import string

app = Flask(__name__)

# Crear una instancia global de la lista enlazada y variables de resumen
mensajes = ListaEnlazada()
resumen_global = {"total": 0, "positivos": 0, "negativos": 0, "neutros": 0}
analisis_empresas = {}
fecha_entrada = None  # Variable para almacenar la fecha del primer mensaje procesado

# Variables globales para almacenar los diccionarios de sentimientos
sentimientos_positivos = []
sentimientos_negativos = []

@app.route("/cargarArchivo", methods=["POST"])
def cargar_archivo():
    global mensajes, resumen_global, analisis_empresas, fecha_entrada
    global sentimientos_positivos, sentimientos_negativos

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
    global mensajes, resumen_global, analisis_empresas, fecha_entrada
    global sentimientos_positivos, sentimientos_negativos  # Añade esto

    # Reiniciar todos los datos a su estado inicial
    mensajes = ListaEnlazada()
    resumen_global = {"total": 0, "positivos": 0, "negativos": 0, "neutros": 0}
    analisis_empresas = {}
    fecha_entrada = None
    
    # Reiniciar los sentimientos
    sentimientos_positivos = []
    sentimientos_negativos = []

    return jsonify({"message": "La base de datos se ha restablecido exitosamente."}), 200
@app.route("/consultarDatos", methods=["GET"])
def consultar_datos():
    # Crear la estructura XML personalizada, usando la fecha del archivo de entrada
    fecha_respuesta = fecha_entrada or "Fecha no disponible"
    response_data = {
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

        response_data["respuesta"]["analisis"]["empresa"].append(empresa_data)

    # Generar el XML sin la etiqueta raíz duplicada
    datos_xml = dicttoxml.dicttoxml(response_data, custom_root="lista_respuestas", attr_type=False)
    return Response(datos_xml, mimetype="application/xml")

@app.route("/analizarMensajePrueba", methods=["POST"])
def analizar_mensaje_prueba():
    global sentimientos_positivos, sentimientos_negativos

    # Obtener el mensaje en formato XML
    xml_data = request.data.decode("utf-8")
    mensaje_dict = xmltodict.parse(xml_data)

    # Extraer el contenido del mensaje usando expresiones regulares
    mensaje_texto = mensaje_dict.get("mensaje", "")
    datos_mensaje = extraer_datos_mensaje(mensaje_texto)

    # Limpiar el mensaje para asegurar consistencia en las comparaciones
    mensaje_limpio = limpiar_mensaje(mensaje_texto)

    # Clasificar el mensaje según el diccionario cargado previamente
    clasificacion = clasificar_mensaje(mensaje_limpio, sentimientos_positivos, sentimientos_negativos)

    # Contar palabras positivas y negativas utilizando limpiar_palabra
    positivos = sum(1 for palabra in mensaje_limpio.split() if limpiar_palabra(palabra) in [limpiar_palabra(p) for p in sentimientos_positivos])
    negativos = sum(1 for palabra in mensaje_limpio.split() if limpiar_palabra(palabra) in [limpiar_palabra(p) for p in sentimientos_negativos])

    # Calcular el porcentaje de sentimiento
    total_palabras = positivos + negativos
    porcentaje_positivo = (positivos / total_palabras) * 100 if total_palabras > 0 else 0
    porcentaje_negativo = (negativos / total_palabras) * 100 if total_palabras > 0 else 0

    # Redondear a enteros
    porcentaje_positivo = int(round(porcentaje_positivo))
    porcentaje_negativo = int(round(porcentaje_negativo))

    # Determinar el sentimiento analizado
    sentimiento_analizado = "positivo" if positivos > negativos else "negativo" if negativos > positivos else "neutro"

    # Estructurar la respuesta en XML
    respuesta = {
        "respuesta": {
            "fecha": datos_mensaje["fecha"],
            "red_social": datos_mensaje["red_social"],
            "usuario": datos_mensaje["usuario"],
            "palabras_positivas": positivos,
            "palabras_negativas": negativos,
            "sentimiento_positivo": f"{porcentaje_positivo}%",
            "sentimiento_negativo": f"{porcentaje_negativo}%",
            "sentimiento_analizado": sentimiento_analizado
        }
    }

    # Convertir a XML y enviar respuesta
    xml_respuesta = dicttoxml.dicttoxml(respuesta, attr_type=False)
    return Response(xml_respuesta, mimetype="application/xml")

def clasificar_mensaje(mensaje, sentimientos_positivos, sentimientos_negativos):
    sentimientos_positivos = [limpiar_palabra(palabra) for palabra in sentimientos_positivos if isinstance(palabra, str)]
    sentimientos_negativos = [limpiar_palabra(palabra) for palabra in sentimientos_negativos if isinstance(palabra, str)]

    mensaje_palabras = limpiar_mensaje(mensaje).split()

    positivos = sum(1 for palabra in mensaje_palabras if palabra in sentimientos_positivos)
    negativos = sum(1 for palabra in mensaje_palabras if palabra in sentimientos_negativos)

    if positivos > negativos:
        return "positivo"
    elif negativos > positivos:
        return "negativo"
    else:
        return "neutro"

def limpiar_mensaje(mensaje):
    mensaje = mensaje.lower()
    mensaje = re.sub(r'[áÁ]', 'a', mensaje)
    mensaje = re.sub(r'[éÉ]', 'e', mensaje)
    mensaje = re.sub(r'[íÍ]', 'i', mensaje)
    mensaje = re.sub(r'[óÓ]', 'o', mensaje)
    mensaje = re.sub(r'[úÚ]', 'u', mensaje)
    mensaje = re.sub(r'[^\w\s]', '', mensaje)
    return mensaje.strip()

def limpiar_palabra(palabra):
    palabra = palabra.lower()
    palabra = re.sub(r'[áÁ]', 'a', palabra)
    palabra = re.sub(r'[éÉ]', 'e', palabra)
    palabra = re.sub(r'[íÍ]', 'i', palabra)
    palabra = re.sub(r'[óÓ]', 'o', palabra)
    palabra = re.sub(r'[úÚ]', 'u', palabra)
    palabra = re.sub(r'[^\w]', '', palabra)
    return palabra.strip()

def procesar_alias(alias_servicio):
    return list(set(alias_servicio)) if isinstance(alias_servicio, list) else alias_servicio

def extraer_datos_mensaje(mensaje):
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
@app.route("/resumen_clasificacion_por_fecha", methods=["GET"])
def resumen_clasificacion_por_fecha():
    # Obtener los parámetros de fecha y empresa desde la URL
    fecha = request.args.get("fecha")  # Formato esperado: "dd/mm/yyyy"
    empresa = request.args.get("empresa", "").lower()  # Empresa opcional, en minúsculas

    # Validar que la fecha esté proporcionada
    if not fecha:
        return jsonify({"error": "Debe especificar una fecha en el formato dd/mm/yyyy."}), 400

    # Inicializar contadores de resumen general
    resumen = {"total": 0, "positivos": 0, "negativos": 0, "neutros": 0}

    # Si una empresa específica fue seleccionada
    if empresa:
        # Verificar si la empresa existe en el análisis
        empresa_data = analisis_empresas.get(empresa)
        if not empresa_data:
            return jsonify({"error": f"La empresa '{empresa}' no tiene datos en el análisis."}), 404

        # Filtrar por mensajes de la empresa en la fecha seleccionada
        for nodo in mensajes.recorrer():
            mensaje = nodo["mensaje"]
            clasificacion = nodo["clasificacion"]

            # Validar si el mensaje coincide con la fecha seleccionada
            if mensaje["fecha"].split()[0] == fecha:
                resumen["total"] += 1
                if clasificacion == "positivo":
                    resumen["positivos"] += 1
                elif clasificacion == "negativo":
                    resumen["negativos"] += 1
                else:
                    resumen["neutros"] += 1

    else:
        # Si no se especifica una empresa, sumar todos los mensajes en la fecha
        for nodo in mensajes.recorrer():
            mensaje = nodo["mensaje"]
            clasificacion = nodo["clasificacion"]

            # Validar si el mensaje coincide con la fecha seleccionada
            if mensaje["fecha"].split()[0] == fecha:
                resumen["total"] += 1
                if clasificacion == "positivo":
                    resumen["positivos"] += 1
                elif clasificacion == "negativo":
                    resumen["negativos"] += 1
                else:
                    resumen["neutros"] += 1

    # Devolver el resumen en formato JSON para que el frontend lo procese
    return jsonify({
        "fecha": fecha,
        "empresa": empresa if empresa else "Todas las empresas",
        "resumen": resumen
    }), 200


if __name__ == "__main__":
    app.run(debug=True, port=8001)
