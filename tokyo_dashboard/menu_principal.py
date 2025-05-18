import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog

def ejecutar_script(nombre_script):
    """Busca y ejecuta un script Python."""
    # Obtener directorio actual
    dir_actual = os.path.dirname(os.path.abspath(__file__))
    
    # Posibles ubicaciones para el script
    posibles_rutas = [
        os.path.join(dir_actual, nombre_script),
        os.path.join(dir_actual, "tokyo_dashboard", nombre_script),
        os.path.join(dir_actual, "..", nombre_script),
        nombre_script
    ]
    
    # Buscar el script en las posibles ubicaciones
    ruta_encontrada = None
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            ruta_encontrada = ruta
            break
    
    # Si no se encuentra, permitir selección manual
    if not ruta_encontrada:
        messagebox.showinfo("Seleccionar Archivo", 
                           f"No se encontró automáticamente el archivo '{nombre_script}'.\n"
                           "Por favor, selecciónelo manualmente.")
        ruta_encontrada = filedialog.askopenfilename(
            title=f"Seleccionar archivo {nombre_script}",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        
        if not ruta_encontrada:
            messagebox.showerror("Operación Cancelada", "No se seleccionó ningún archivo.")
            return False
    
    # Ejecutar el script
    try:
        subprocess.Popen([sys.executable, ruta_encontrada])
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Error al ejecutar el script: {e}")
        return False

class MenuPrincipal:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Monitoreo Arduino")
        self.root.geometry("400x300")
        self.root.resizable(True, True)
        
        # Configurar la interfaz
        self.configurar_interfaz()
    
    def configurar_interfaz(self):
        # Marco principal
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        titulo = tk.Label(main_frame, text="Sistema de Monitoreo Arduino", 
                         font=("Arial", 16, "bold"))
        titulo.pack(pady=10)
        
        # Descripción
        descripcion = tk.Label(main_frame, text="Seleccione una opción para iniciar:", 
                             font=("Arial", 10))
        descripcion.pack(pady=5)
        
        # Botones
        btn_configuracion = tk.Button(main_frame, text="Configuración del Sistema", 
                                   command=self.abrir_configuracion,
                                   width=25, height=2)
        btn_configuracion.pack(pady=5)
        
        btn_monitor = tk.Button(main_frame, text="Iniciar Monitor Arduino", 
                               command=self.iniciar_monitor,
                               width=25, height=2)
        btn_monitor.pack(pady=5)
        
        btn_dashboard = tk.Button(main_frame, text="Iniciar Dashboard", 
                                command=self.iniciar_dashboard,
                                width=25, height=2)
        btn_dashboard.pack(pady=5)
        
        btn_salir = tk.Button(main_frame, text="Salir", 
                            command=self.root.destroy,
                            width=25, height=2)
        btn_salir.pack(pady=5)
        
        # Información
        info = tk.Label(main_frame, text="© 2025 Sistema de Monitoreo Arduino", 
                       font=("Arial", 8), fg="gray")
        info.pack(side=tk.BOTTOM, pady=10)
    
    def abrir_configuracion(self):
        if ejecutar_script("configuracion_app.py"):
            messagebox.showinfo("Éxito", "La aplicación de configuración se ha iniciado.")
    
    def iniciar_monitor(self):
        if ejecutar_script("monitor_arduino.py"):
            messagebox.showinfo("Éxito", "El monitor Arduino se ha iniciado.")
    
    def iniciar_dashboard(self):
        if ejecutar_script("main.py"):
            messagebox.showinfo("Éxito", "El dashboard se ha iniciado.")

def main():
    root = tk.Tk()
    app = MenuPrincipal(root)
    root.mainloop()

if __name__ == "__main__":
    main()