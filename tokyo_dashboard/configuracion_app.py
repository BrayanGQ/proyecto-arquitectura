import os
import sys
import psycopg2
import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import subprocess
import time
from datetime import datetime

class ConfiguracionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Configuración del Sistema de Monitoreo Arduino")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Variables de configuración
        self.db_host = tk.StringVar(value="localhost")
        self.db_port = tk.StringVar(value="5432")
        self.db_name = tk.StringVar(value="arduino_monitoreo")
        self.db_user = tk.StringVar(value="postgres")
        self.db_password = tk.StringVar(value="Matematicas1")
        
        self.puerto_com = tk.StringVar(value="COM3")
        self.baudrate = tk.StringVar(value="9600")
        
        self.umbral_temperatura = tk.DoubleVar(value=70.0)
        self.umbral_vibracion = tk.IntVar(value=900)
        
        # Crear la interfaz
        self.crear_interfaz()
    
    def crear_interfaz(self):
        # Notebook para pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña de base de datos
        tab_db = ttk.Frame(notebook)
        notebook.add(tab_db, text="Base de Datos")
        self.crear_tab_db(tab_db)
        
        # Pestaña de Arduino
        tab_arduino = ttk.Frame(notebook)
        notebook.add(tab_arduino, text="Arduino")
        self.crear_tab_arduino(tab_arduino)
        
        # Pestaña de Umbrales
        tab_umbrales = ttk.Frame(notebook)
        notebook.add(tab_umbrales, text="Umbrales")
        self.crear_tab_umbrales(tab_umbrales)
        
        # Pestaña de pruebas
        tab_pruebas = ttk.Frame(notebook)
        notebook.add(tab_pruebas, text="Pruebas")
        self.crear_tab_pruebas(tab_pruebas)
        
        # Botones de acción en la parte inferior
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Guardar Configuración", 
                  command=self.guardar_configuracion).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Iniciar Monitor", 
                  command=self.iniciar_monitor).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Iniciar Dashboard", 
                  command=self.iniciar_dashboard).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Salir", 
                  command=self.root.destroy).pack(side=tk.RIGHT, padx=5)
    
    def crear_tab_db(self, parent):
        frame = ttk.LabelFrame(parent, text="Configuración de PostgreSQL", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Host
        ttk.Label(frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.db_host, width=30).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Puerto
        ttk.Label(frame, text="Puerto:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.db_port, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Nombre de BD
        ttk.Label(frame, text="Base de datos:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.db_name, width=20).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Usuario
        ttk.Label(frame, text="Usuario:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.db_user, width=20).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Contraseña
        ttk.Label(frame, text="Contraseña:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.db_password, width=20, show="*").grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Botón de prueba
        ttk.Button(frame, text="Probar Conexión", 
                  command=self.probar_conexion_bd).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Botón para crear base de datos
        ttk.Button(frame, text="Crear Base de Datos", 
                  command=self.crear_base_datos).grid(row=6, column=0, columnspan=2, pady=5)
    
    def crear_tab_arduino(self, parent):
        frame = ttk.LabelFrame(parent, text="Configuración de Arduino", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Puerto COM
        ttk.Label(frame, text="Puerto COM:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(frame, textvariable=self.puerto_com, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Velocidad (baudrate)
        ttk.Label(frame, text="Baudrate:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(frame, textvariable=self.baudrate, 
                    values=("9600", "19200", "38400", "57600", "115200")).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Botón para detectar puertos
        ttk.Button(frame, text="Detectar Puertos Disponibles", 
                  command=self.detectar_puertos).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Botón para probar Arduino
        ttk.Button(frame, text="Probar Conexión Arduino", 
                  command=self.probar_conexion_arduino).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Lista de puertos disponibles
        self.puertos_listbox = tk.Listbox(frame, height=5, width=30)
        self.puertos_listbox.grid(row=4, column=0, columnspan=2, pady=10)
        self.puertos_listbox.bind("<Double-Button-1>", self.seleccionar_puerto)
    
    def crear_tab_umbrales(self, parent):
        frame = ttk.LabelFrame(parent, text="Umbrales para Alertas", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Umbral de temperatura
        ttk.Label(frame, text="Umbral de temperatura (°C):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Scale(frame, from_=30, to=100, variable=self.umbral_temperatura, 
                 orient=tk.HORIZONTAL, length=200).grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, textvariable=self.umbral_temperatura).grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Umbral de vibración
        ttk.Label(frame, text="Umbral de vibración:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Scale(frame, from_=500, to=1000, variable=self.umbral_vibracion, 
                 orient=tk.HORIZONTAL, length=200).grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, textvariable=self.umbral_vibracion).grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Información sobre umbrales
        info_text = """
        Estos umbrales determinan cuándo se activarán las alertas:
        
        - Temperatura: Una lectura superior a este valor generará una alerta de incendio.
        - Vibración: Una lectura superior a este valor generará una alerta de terremoto.
        
        Ajuste estos valores según la sensibilidad deseada y las características
        de sus sensores. Valores más bajos generarán más alertas (mayor sensibilidad).
        """
        
        info_label = ttk.Label(frame, text=info_text, wraplength=500, justify=tk.LEFT)
        info_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=10)
    
    def crear_tab_pruebas(self, parent):
        frame = ttk.LabelFrame(parent, text="Pruebas y Diagnóstico", padding=10)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Botones de prueba para diferentes eventos
        ttk.Button(frame, text="Insertar Evento de Temperatura", 
                  command=lambda: self.insertar_evento_prueba("Temperatura")).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        ttk.Button(frame, text="Insertar Alerta de Terremoto", 
                  command=lambda: self.insertar_evento_prueba("Alerta Sismica")).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        ttk.Button(frame, text="Insertar Alerta de Incendio", 
                  command=lambda: self.insertar_evento_prueba("Incendio")).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        ttk.Button(frame, text="Insertar Evento de Peatones", 
                  command=lambda: self.insertar_evento_prueba("Trafico Peatonal")).grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Área para resultados
        ttk.Label(frame, text="Resultados de pruebas:").grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        self.resultados_text = tk.Text(frame, width=40, height=10)
        self.resultados_text.grid(row=1, column=1, rowspan=3, sticky=tk.NSEW, padx=10)
        
        # Scrollbar para el área de resultados
        scrollbar = ttk.Scrollbar(frame, command=self.resultados_text.yview)
        scrollbar.grid(row=1, column=2, rowspan=3, sticky=tk.NS)
        self.resultados_text.config(yscrollcommand=scrollbar.set)
        
        # Botón para limpiar área de resultados
        ttk.Button(frame, text="Limpiar Resultados", 
                  command=lambda: self.resultados_text.delete(1.0, tk.END)).grid(row=4, column=1, sticky=tk.W, pady=5)
    
    def guardar_configuracion(self):
        """Guarda la configuración actual en un archivo Python."""
        try:
            with open("config_arduino.py", "w") as f:
                f.write("# Configuración del Sistema de Monitoreo Arduino\n")
                f.write("# Generado automáticamente por la herramienta de configuración\n")
                f.write(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("CONFIG = {\n")
                f.write(f"    'puerto_com': '{self.puerto_com.get()}',\n")
                f.write(f"    'baudrate': {self.baudrate.get()},\n\n")
                
                f.write(f"    'db_host': '{self.db_host.get()}',\n")
                f.write(f"    'db_port': '{self.db_port.get()}',\n")
                f.write(f"    'db_name': '{self.db_name.get()}',\n")
                f.write(f"    'db_user': '{self.db_user.get()}',\n")
                f.write(f"    'db_password': '{self.db_password.get()}',\n\n")
                
                f.write(f"    'umbral_temperatura_alta': {self.umbral_temperatura.get()},\n")
                f.write(f"    'umbral_vibracion': {self.umbral_vibracion.get()},\n\n")
                
                f.write("    'intervalo_temperatura': 30,\n")
                f.write("    'intervalo_terremoto': 60,\n")
                f.write("    'intervalo_incendio': 60,\n")
                f.write("    'intervalo_peatones': 10\n")
                f.write("}\n")
            
            messagebox.showinfo("Configuración Guardada", 
                               "La configuración se ha guardado correctamente en 'config_arduino.py'")
            
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar configuración: {e}")
            return False
    
    def probar_conexion_bd(self):
        """Prueba la conexión a la base de datos PostgreSQL."""
        try:
            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                user=self.db_user.get(),
                password=self.db_password.get()
            )
            
            # Verificar si la base de datos existe
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (self.db_name.get(),))
            exists = cursor.fetchone()
            
            if exists:
                messagebox.showinfo("Conexión Exitosa", 
                                   f"Se ha conectado correctamente a PostgreSQL.\n\n"
                                   f"La base de datos '{self.db_name.get()}' existe.")
            else:
                messagebox.showwarning("Conexión Exitosa / Base de Datos No Existe", 
                                     f"Se ha conectado correctamente a PostgreSQL.\n\n"
                                     f"La base de datos '{self.db_name.get()}' NO existe.\n"
                                     f"Puede crearla con el botón 'Crear Base de Datos'.")
            
            conn.close()
            return True
        except Exception as e:
            messagebox.showerror("Error de Conexión", 
                                f"No se pudo conectar a PostgreSQL:\n\n{e}")
            return False
    
    def crear_base_datos(self):
        """Crea la base de datos y la tabla eventos si no existen."""
        try:
            # Conectar a PostgreSQL (no a una base de datos específica)
            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                user=self.db_user.get(),
                password=self.db_password.get(),
                database="postgres"  # Conectar a la base de datos postgres por defecto
            )
            conn.autocommit = True  # Necesario para crear bases de datos
            cursor = conn.cursor()
            
            # Verificar si la base de datos existe
            cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (self.db_name.get(),))
            if not cursor.fetchone():
                # Crear la base de datos
                cursor.execute(f"CREATE DATABASE {self.db_name.get()}")
                self.agregar_resultado(f"Base de datos '{self.db_name.get()}' creada con éxito.")
            else:
                self.agregar_resultado(f"La base de datos '{self.db_name.get()}' ya existe.")
            
            conn.close()
            
            # Conectar a la base de datos creada
            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                user=self.db_user.get(),
                password=self.db_password.get(),
                database=self.db_name.get()
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Verificar si la tabla eventos existe
            cursor.execute("SELECT to_regclass('public.eventos')")
            if not cursor.fetchone()[0]:
                # Crear la tabla eventos
                cursor.execute("""
                CREATE TABLE eventos (
                    id SERIAL PRIMARY KEY,
                    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ubicacion VARCHAR(100) NOT NULL,
                    tipo_evento VARCHAR(100) NOT NULL,
                    descripcion TEXT,
                    sensor VARCHAR(100) NOT NULL
                )
                """)
                self.agregar_resultado("Tabla 'eventos' creada con éxito.")
                
                # Insertar datos de prueba
                datos = [
                    ('Tokio', 'Sistema', 'Sistema de monitoreo iniciado', 'Arduino'),
                    ('Tokio', 'Temperatura', 'Temperatura registrada: 25.5 C', 'LM35'),
                    ('Tokio', 'Alerta Sismica', 'Se ha detectado actividad sismica. Mantenga la calma.', 'SW-18010P'),
                    ('Tokio', 'Incendio', 'Se ha detectado un posible incendio. Temperatura: 70.3 C', 'LM35'),
                    ('Cruce de Shibuya', 'Trafico Peatonal', 'Se ha detectado movimiento de peatones en el cruce.', 'PIR')
                ]
                
                for dato in datos:
                    cursor.execute("""
                    INSERT INTO eventos (ubicacion, tipo_evento, descripcion, sensor)
                    VALUES (%s, %s, %s, %s)
                    """, dato)
                
                self.agregar_resultado("Datos de ejemplo insertados en la tabla.")
            else:
                self.agregar_resultado("La tabla 'eventos' ya existe.")
            
            conn.close()
            
            messagebox.showinfo("Base de Datos Preparada", 
                              f"La base de datos '{self.db_name.get()}' está lista para usar.")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear base de datos: {e}")
            self.agregar_resultado(f"ERROR: {e}")
            return False
    
    def detectar_puertos(self):
        """Detecta los puertos COM disponibles."""
        try:
            self.puertos_listbox.delete(0, tk.END)
            puertos = list(serial.tools.list_ports.comports())
            
            if not puertos:
                self.agregar_resultado("No se encontraron puertos COM disponibles.")
                return
            
            for puerto in puertos:
                self.puertos_listbox.insert(tk.END, f"{puerto.device} - {puerto.description}")
                self.agregar_resultado(f"Puerto encontrado: {puerto.device} - {puerto.description}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al detectar puertos: {e}")
            self.agregar_resultado(f"ERROR: {e}")
    
    def seleccionar_puerto(self, event):
        """Selecciona un puerto de la lista."""
        seleccion = self.puertos_listbox.curselection()
        if seleccion:
            puerto = self.puertos_listbox.get(seleccion[0]).split(" - ")[0]
            self.puerto_com.set(puerto)
            self.agregar_resultado(f"Puerto seleccionado: {puerto}")
    
    def probar_conexion_arduino(self):
        """Prueba la conexión con el Arduino."""
        try:
            puerto = self.puerto_com.get()
            baudrate = int(self.baudrate.get())
            
            # Intentar abrir el puerto
            ser = serial.Serial(puerto, baudrate, timeout=1)
            
            if ser.is_open:
                self.agregar_resultado(f"Conexión exitosa al puerto {puerto} a {baudrate} baudios.")
                
                # Esperar datos por 3 segundos
                self.agregar_resultado("Esperando datos del Arduino (3 segundos)...")
                
                inicio = time.time()
                datos_recibidos = False
                
                while time.time() - inicio < 3:
                    if ser.in_waiting > 0:
                        linea = ser.readline().decode('ascii', errors='replace').strip()
                        if linea:
                            self.agregar_resultado(f"Datos recibidos: {linea}")
                            datos_recibidos = True
                    time.sleep(0.1)
                
                if not datos_recibidos:
                    self.agregar_resultado("No se recibieron datos en 3 segundos.")
                
                ser.close()
                messagebox.showinfo("Conexión Arduino", 
                                  f"Prueba de conexión al puerto {puerto} completada.")
            else:
                messagebox.showerror("Error", f"No se pudo abrir el puerto {puerto}.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al conectar con Arduino: {e}")
            self.agregar_resultado(f"ERROR: {e}")
    
    def insertar_evento_prueba(self, tipo_evento):
        """Inserta un evento de prueba en la base de datos."""
        try:
            conn = psycopg2.connect(
                host=self.db_host.get(),
                port=self.db_port.get(),
                database=self.db_name.get(),
                user=self.db_user.get(),
                password=self.db_password.get()
            )
            cursor = conn.cursor()
            
            ubicacion = "Tokio"
            sensor = "Test"
            descripcion = ""
            
            if tipo_evento == "Temperatura":
                temperatura = self.umbral_temperatura.get() - 10  # Valor seguro por debajo del umbral
                descripcion = f"Temperatura registrada: {temperatura} C"
                sensor = "LM35"
            elif tipo_evento == "Alerta Sismica":
                descripcion = "Se ha detectado actividad sismica. Mantenga la calma y siga los protocolos de seguridad."
                sensor = "SW-18010P"
            elif tipo_evento == "Incendio":
                temperatura = self.umbral_temperatura.get() + 5  # Valor por encima del umbral
                descripcion = f"Se ha detectado un posible incendio. Temperatura: {temperatura} C"
                sensor = "LM35"
            elif tipo_evento == "Trafico Peatonal":
                descripcion = "Se ha detectado movimiento de peatones en el cruce."
                ubicacion = "Cruce de Shibuya"
                sensor = "PIR"
            
            cursor.execute("""
            INSERT INTO eventos (ubicacion, tipo_evento, descripcion, sensor)
            VALUES (%s, %s, %s, %s)
            RETURNING id, fecha_hora
            """, (ubicacion, tipo_evento, descripcion, sensor))
            
            id_evento, fecha_hora = cursor.fetchone()
            conn.commit()
            
            self.agregar_resultado(f"Evento de prueba insertado: ID {id_evento}")
            self.agregar_resultado(f"Tipo: {tipo_evento}")
            self.agregar_resultado(f"Descripción: {descripcion}")
            self.agregar_resultado(f"Fecha: {fecha_hora}")
            self.agregar_resultado("-" * 40)
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al insertar evento de prueba: {e}")
            self.agregar_resultado(f"ERROR: {e}")
    
    def agregar_resultado(self, texto):
        """Agrega texto al área de resultados."""
        self.resultados_text.insert(tk.END, f"{texto}\n")
        self.resultados_text.see(tk.END)  # Desplazar al final
    
    def iniciar_monitor(self):
        """Inicia el monitor de Arduino en un proceso separado."""
        if not self.guardar_configuracion():
            return
        
        try:
            # Verificar si el script existe
            if not os.path.exists("monitor_arduino.py"):
                messagebox.showerror("Error", "No se encontró el archivo 'monitor_arduino.py'")
                return
            
            # Iniciar el proceso
            subprocess.Popen([sys.executable, "monitor_arduino.py"])
            
            messagebox.showinfo("Monitor Iniciado", 
                              "El monitor Arduino se ha iniciado en una nueva ventana.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar el monitor: {e}")
    
    def iniciar_dashboard(self):
        """Inicia el dashboard en un proceso separado."""
        try:
            # Verificar si el archivo existe (asumiendo que tu dashboard principal es 'main.py')
            dashboard_file = "main.py"
            if not os.path.exists(dashboard_file):
                messagebox.showerror("Error", f"No se encontró el archivo '{dashboard_file}'")
                return
            
            # Iniciar el proceso
            subprocess.Popen([sys.executable, dashboard_file])
            
            messagebox.showinfo("Dashboard Iniciado", 
                             "El dashboard se ha iniciado en una nueva ventana.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar el dashboard: {e}")

# Función principal
def main():
    root = tk.Tk()
    app = ConfiguracionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()