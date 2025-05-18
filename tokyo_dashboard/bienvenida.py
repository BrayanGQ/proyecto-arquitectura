# bienvenida.py
import tkinter as tk
from PIL import Image, ImageTk
from dashboard import Dashboard

class VentanaBienvenida:
    def __init__(self, root):
        self.root = root
        self.root.title("Bienvenida")

        ancho_ventana = 500
        alto_ventana = 400

        # Obtener dimensiones de pantalla
        ancho_pantalla = root.winfo_screenwidth()
        alto_pantalla = root.winfo_screenheight()

        # Calcular posición centrada
        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)

        # Aplicar tamaño y posición
        root.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        root.resizable(False, False)

        # Imagen decorativa
        ruta_imagen = r"C:\Users\braya\Documents\Arquitectura de Computadoras\Imagen de Portada.jpg"
        try:
            imagen = Image.open(ruta_imagen)
            imagen = imagen.resize((300, 180))
            self.tkimage = ImageTk.PhotoImage(imagen)
            tk.Label(root, image=self.tkimage).pack(pady=10)
        except Exception as e:
            print("No se pudo cargar la imagen:", e)

        tk.Label(root, text="Bienvenidos a la Ciudad Inteligente de Tokio", 
                 font=("Arial", 14), wraplength=400, justify="center").pack(pady=20)

        tk.Button(root, text="Ingresar al Dashboard", command=self.ingresar, 
                  font=("Arial", 12), width=25).pack()

    def ingresar(self):
        self.root.destroy()
        nuevo_root = tk.Tk()
        Dashboard(nuevo_root)
        nuevo_root.mainloop()
