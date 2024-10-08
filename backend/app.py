from flask import Flask, request, jsonify
import dicttoxml
app = Flask(__name__)

@app.route("/cargarArchivo", methods=["Post"])
def cargar_archivo():
    body = request.json
    print(body)
    print("")


    xml = dicttoxml.dicttoxml(body)
    print(xml)


    return jsonify({"message": "se cargo con exito. "})

if __name__ == "__main__":
    app.run(debug=True, port= 8001)
