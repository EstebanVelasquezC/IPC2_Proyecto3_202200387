from flask import Flask, request, jsonify
import dicttoxml
from tda import ListaEnlazada

app = Flask(__name__)

# Inicializar una nueva lista enlazada para cada solicitud
@app.route("/cargarArchivo", methods=["POST"])
def cargar_archivo():
    mensajes = ListaEnlazada()  # Asegurarse de crear una nueva lista de mensajes en cada solicitud
    body = request.json

    # Variables para almacenar las estadísticas y errores
    total_mensajes = 0
    total_positivos = 0
    total_negativos = 0
    total_neutros = 0
    errores = []  # Para registrar errores en los mensajes

    # Estructura para almacenar análisis por empresa y servicio
    analisis_empresas = {}

    # Verifica si se recibió un JSON válido
    if not body:
        return jsonify({"error": "No JSON received"}), 400

    # Obtener el diccionario de sentimientos y empresas del JSON
    try:
        diccionario = body.get("solicitud_clasificacion", {}).get("diccionario", {})
        sentimientos_positivos = diccionario.get("sentimientos_positivos", {}).get("palabra", [])
        sentimientos_negativos = diccionario.get("sentimientos_negativos", {}).get("palabra", [])
        empresas_analizar = diccionario.get("empresas_analizar", {}).get("empresa", [])

        # Asegurarse de que empresas_analizar siempre sea una lista
        if isinstance(empresas_analizar, dict):  # Si es un solo elemento, lo convertimos en lista
            empresas_analizar = [empresas_analizar]

        # Procesar los mensajes
        lista_mensajes = body.get("solicitud_clasificacion", {}).get("lista_mensajes", {}).get("mensaje", [])

        # Clasificar y almacenar los mensajes
        for mensaje in lista_mensajes:
            try:
                clasificacion = clasificar_mensaje(mensaje, sentimientos_positivos, sentimientos_negativos)
                mensajes.agregar({"mensaje": mensaje, "clasificacion": clasificacion})

                # Actualizar las estadísticas generales
                total_mensajes += 1
                if clasificacion == "positivo":
                    total_positivos += 1
                elif clasificacion == "negativo":
                    total_negativos += 1
                else:
                    total_neutros += 1

                # Analizar las empresas y servicios mencionados en el mensaje
                for empresa in empresas_analizar:
                    nombre_empresa = empresa.get("nombre", "").lower()
                    servicios = empresa.get("servicios", {}).get("servicio", [])

                    # Asegurarse de que servicios siempre sea una lista
                    if isinstance(servicios, dict):  # Si es un solo servicio, convertirlo en lista
                        servicios = [servicios]

                    # Inicializar la empresa si no está en el análisis
                    if nombre_empresa not in analisis_empresas:
                        analisis_empresas[nombre_empresa] = {
                            "total": 0, "positivos": 0, "negativos": 0, "neutros": 0, "servicios": {}
                        }

                    # Analizar los servicios mencionados
                    empresa_mencionada = False  # Para verificar si la empresa es mencionada

                    # Verificar si la empresa es mencionada en el mensaje (insensible a mayúsculas/minúsculas)
                    if nombre_empresa in mensaje.lower():  # Convertir el mensaje a minúsculas también
                        empresa_mencionada = True

                    for servicio in servicios:
                        nombre_servicio = servicio.get("@nombre", "").lower()
                        alias_servicio = procesar_alias(servicio.get("alias", []))  # Eliminar duplicados

                        # Asegurarse de que alias_servicio siempre sea una lista
                        if isinstance(alias_servicio, str):
                            alias_servicio = [alias_servicio]

                        # Verificar si el servicio o sus alias son mencionados en el mensaje
                        if any(alias.lower() in mensaje.lower() for alias in alias_servicio) or nombre_servicio in mensaje.lower():
                            empresa_mencionada = True
                            if nombre_servicio not in analisis_empresas[nombre_empresa]["servicios"]:
                                analisis_empresas[nombre_empresa]["servicios"][nombre_servicio] = {
                                    "total": 0, "positivos": 0, "negativos": 0, "neutros": 0
                                }

                            # Actualizar el conteo del servicio
                            analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["total"] += 1
                            if clasificacion == "positivo":
                                analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["positivos"] += 1
                            elif clasificacion == "negativo":
                                analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["negativos"] += 1
                            else:
                                analisis_empresas[nombre_empresa]["servicios"][nombre_servicio]["neutros"] += 1

                    # Si la empresa es mencionada en algún servicio, se cuenta en el total
                    if empresa_mencionada:
                        analisis_empresas[nombre_empresa]["total"] += 1
                        if clasificacion == "positivo":
                            analisis_empresas[nombre_empresa]["positivos"] += 1
                        elif clasificacion == "negativo":
                            analisis_empresas[nombre_empresa]["negativos"] += 1
                        else:
                            analisis_empresas[nombre_empresa]["neutros"] += 1

            except Exception as e:
                errores.append(f"Error en el mensaje: {mensaje[:30]}... - {str(e)}")  # Agregar error y continuar

        # Asegurarse de incluir todos los servicios aunque no hayan sido mencionados
        for empresa in empresas_analizar:
            nombre_empresa = empresa.get("nombre", "").lower()
            servicios = empresa.get("servicios", {}).get("servicio", [])

            # Asegurarse de que servicios siempre sea una lista
            if isinstance(servicios, dict):
                servicios = [servicios]

            # Incluir los servicios que no hayan sido mencionados
            for servicio in servicios:
                nombre_servicio = servicio.get("@nombre", "").lower()
                if nombre_servicio not in analisis_empresas[nombre_empresa]["servicios"]:
                    analisis_empresas[nombre_empresa]["servicios"][nombre_servicio] = {
                        "total": 0, "positivos": 0, "negativos": 0, "neutros": 0
                    }

        # Resumen de clasificación
        resumen = {
            "total_mensajes": total_mensajes,
            "positivos": total_positivos,
            "negativos": total_negativos,
            "neutros": total_neutros,
            "analisis_empresas": analisis_empresas,
            "errores": errores
        }

        # Convertir los resultados en XML sin atributos de tipo
        xml = dicttoxml.dicttoxml(mensajes.recorrer(), attr_type=False)  # Evitar los atributos de tipo
        print(xml)

        return jsonify({"message": "se cargó con éxito.", "resumen": resumen})
    except KeyError as e:
        return jsonify({"error": f"Missing key: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def clasificar_mensaje(mensaje, sentimientos_positivos, sentimientos_negativos):
    # Asegurarse de que ambas variables sean listas válidas
    if not isinstance(sentimientos_positivos, list):
        sentimientos_positivos = []
    if not isinstance(sentimientos_negativos, list):
        sentimientos_negativos = []

    # Convertir el mensaje a minúsculas y separar en palabras
    mensaje_palabras = mensaje.lower().split()

    # Filtrar sentimientos que no sean cadenas válidas
    sentimientos_positivos = [palabra.lower() for palabra in sentimientos_positivos if isinstance(palabra, str)]
    sentimientos_negativos = [palabra.lower() for palabra in sentimientos_negativos if isinstance(palabra, str)]

    # Contar palabras positivas y negativas exactas en el mensaje
    positivos = sum(1 for palabra in mensaje_palabras if palabra in sentimientos_positivos)
    negativos = sum(1 for palabra in mensaje_palabras if palabra in sentimientos_negativos)

    # Determinar la clasificación del mensaje
    if positivos > negativos:
        return "positivo"
    elif negativos > positivos:
        return "negativo"
    else:
        return "neutro"

def procesar_alias(alias_servicio):
    """Función para eliminar alias duplicados."""
    if isinstance(alias_servicio, list):
        return list(set(alias_servicio))  # Convertir la lista a un conjunto para eliminar duplicados
    return alias_servicio

if __name__ == "__main__":
    app.run(debug=True, port=8001)
