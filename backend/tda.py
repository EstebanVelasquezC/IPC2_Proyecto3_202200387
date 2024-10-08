# archivo tda.py
class Nodo:
    def __init__(self, mensaje):
        self.mensaje = mensaje
        self.siguiente = None

class ListaEnlazada:
    def __init__(self):
        self.primero = None
        self.tamano = 0  # Atributo para llevar la cuenta de elementos

    def agregar(self, mensaje):
        nuevo_nodo = Nodo(mensaje)
        if not self.primero:
            self.primero = nuevo_nodo
        else:
            actual = self.primero
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo_nodo
        self.tamano += 1  # Incrementar el tamaño al agregar un nuevo nodo

    def recorrer(self):
        mensajes = []
        actual = self.primero
        while actual:
            mensajes.append(actual.mensaje)  # Agregamos el mensaje completo a la lista
            actual = actual.siguiente
        return mensajes  # Devolvemos la lista de mensajes

    def obtener_tamano(self):
        return self.tamano  # Método para devolver el tamaño de la lista
