class Nodo:
    def __init__(self, mensaje):
        self.mensaje = mensaje
        self.siguiente = None

class ListaEnlazada:
    def __init__(self):
        self.primero = None
        self.tamano = 0

    def agregar(self, mensaje):
        nuevo_nodo = Nodo(mensaje)
        if not self.primero:
            self.primero = nuevo_nodo
        else:
            actual = self.primero
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo_nodo
        self.tamano += 1

    def recorrer(self):
        mensajes = []
        actual = self.primero
        while actual:
            mensajes.append(actual.mensaje)
            actual = actual.siguiente
        return mensajes

    def obtener_tamano(self):
        return self.tamano
