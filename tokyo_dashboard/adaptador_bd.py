import os
import sys
import psycopg2
import tkinter as tk
from tkinter import ttk, messagebox
import time
from datetime import datetime

class AdaptadorBD:
    """Herramienta para adaptar la base de datos para compatibilidad con el dashboard."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Adaptador de Base de Datos")
        self.root.geometry("700x500")
        
        # Variables para las configuraciones
        self.origen_host = tk.StringVar(value="localhost")
        self.origen_port = tk.StringVar(value="5432")
        self.origen_name = tk.StringVar(value="arduino_monitoreo")
        self.origen_user = tk.StringVar(value="postgres")
        self.origen_password = tk.StringVar(value="Matematicas")
        
        self.destino_host = tk.StringVar(value="localhost")
        self.destino_port = tk.StringVar(value="5432")
        self.destino_name = tk.StringVar(value="tokyo_db")
        self.destino_user = tk.StringVar(value="postgres")
        self.destino_password = tk.StringVar(value="Matematicas")
        
        # Variables de estado
        self.ultimo_id_sincronizado = 0
        self.ejecutando = False
        self.intervalo_sync = 5  # segundos entre sincronizaciones
        
        # Crear la interfaz
        self.crear_interfaz()
    
    def crear_interfaz(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña de configuración
        tab_config = ttk.Frame(notebook)
        notebook.add(tab_config, text="Configuración")
        self.crear_tab_config(tab_config)
        
        # Pestaña de sincronización
        tab_sync = ttk.Frame(notebook)
        notebook.add(tab_sync, text="Sincronización")
        self.crear_tab_sync(tab_sync)
        
        # Botones de acción
        frame_botones = ttk.Frame(self.root)
        frame_botones.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(frame_botones, text="Salir", 
                  command=self.salir).pack(side=tk.RIGHT, padx=5)
    
    def crear_tab_config(self, parent):
        # Marco para la BD origen
        frame_origen = ttk.LabelFrame(parent, text="Base de Datos Origen (arduino_monitoreo)", padding=10)
        frame_origen.pack(fill=tk.X, padx=10, pady=10)
        
        # Configuración BD origen
        ttk.Label(frame_origen, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_origen, textvariable=self.origen_host, width=20).grid(row=0, column=1, pady=2, padx=5)
        
        ttk.Label(frame_origen, text="Puerto:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_origen, textvariable=self.origen_port, width=10).grid(row=1, column=1, pady=2, padx=5)
        
        ttk.Label(frame_origen, text="Base de datos:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_origen, textvariable=self.origen_name, width=20).grid(row=2, column=1, pady=2, padx=5)
        
        ttk.Label(frame_origen, text="Usuario:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_origen, textvariable=self.origen_user, width=20).grid(row=3, column=1, pady=2, padx=5)
        
        ttk.Label(frame_origen, text="Contraseña:").grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_origen, textvariable=self.origen_password, width=20, show="*").grid(row=4, column=1, pady=2, padx=5)
        
        ttk.Button(frame_origen, text="Probar Conexión",
                 command=lambda: self.probar_conexion("origen")).grid(row=5, column=0, columnspan=2, pady=5)
        
        # Marco para la BD destino
        frame_destino = ttk.LabelFrame(parent, text="Base de Datos Destino (tokyo_db)", padding=10)
        frame_destino.pack(fill=tk.X, padx=10, pady=10)
        
        # Configuración BD destino
        ttk.Label(frame_destino, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_destino, textvariable=self.destino_host, width=20).grid(row=0, column=1, pady=2, padx=5)
        
        ttk.Label(frame_destino, text="Puerto:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_destino, textvariable=self.destino_port, width=10).grid(row=1, column=1, pady=2, padx=5)
        
        ttk.Label(frame_destino, text="Base de datos:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_destino, textvariable=self.destino_name, width=20).grid(row=2, column=1, pady=2, padx=5)
        
        ttk.Label(frame_destino, text="Usuario:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_destino, textvariable=self.destino_user, width=20).grid(row=3, column=1, pady=2, padx=5)
        
        ttk.Label(frame_destino, text="Contraseña:").grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame_destino, textvariable=self.destino_password, width=20, show="*").grid(row=4, column=1, pady=2, padx=5)
        
        ttk.Button(frame_destino, text="Probar Conexión",
                 command=lambda: self.probar_conexion("destino")).grid(row=5, column=0, columnspan=2, pady=5)
        
        # Botón para crear la BD destino si no existe
        ttk.Button(frame_destino, text="Crear Base de Datos si No Existe",
                 command=self.crear_bd_destino).grid(row=6, column=0, columnspan=2, pady=5)
        
        # Botón de guardar configuración
        ttk.Button(parent, text="Guardar Configuración",
                 command=self.guardar_configuracion).pack(pady=10)
    
    def crear_tab_sync(self, parent):
        # Marco de controles
        frame_controles = ttk.Frame(parent, padding=10)
        frame_controles.pack(fill=tk.X, padx=10, pady=10)
        
        # Controles de sincronización
        ttk.Button(frame_controles, text="Iniciar Sincronización",
                 command=self.iniciar_sincronizacion).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_controles, text="Detener Sincronización",
                 command=self.detener_sincronizacion).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(frame_controles, text="Sincronizar Ahora",
                 command=self.sincronizar_ahora).pack(side=tk.LEFT, padx=5)
        
        # Área de log
        frame_log = ttk.LabelFrame(parent, text="Registro de Sincronización", padding=10)
        frame_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Texto de log con scrollbar
        scrollbar = ttk.Scrollbar(frame_log)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(frame_log, height=15, width=80, yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Botón para limpiar log
        ttk.Button(frame_log, text="Limpiar Log",
                 command=lambda: self.log_text.delete(1.0, tk.END)).pack(pady=5)
    
    def agregar_log(self, mensaje):
        """Agrega un mensaje al área de log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.log_text.see(tk.END)  # Scroll al final
    
    def probar_conexion(self, tipo):
        """Prueba la conexión a la base de datos especificada."""
        try:
            if tipo == "origen":
                conn = psycopg2.connect(
                    host=self.origen_host.get(),
                    port=self.origen_port.get(),
                    database=self.origen_name.get(),
                    user=self.origen_user.get(),
                    password=self.origen_password.get()
                )
                nombre_bd = self.origen_name.get()
            else:  # destino
                # Para el destino, primero verificar si existe la BD
                conn_postgres = psycopg2.connect(
                    host=self.destino_host.get(),
                    port=self.destino_port.get(),
                    database="postgres",
                    user=self.destino_user.get(),
                    password=self.destino_password.get()
                )
                cur = conn_postgres.cursor()
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.destino_name.get(),))
                exists = cur.fetchone()
                conn_postgres.close()
                
                if not exists:
                    messagebox.showwarning("Base de Datos No Existe", 
                                         f"La base de datos '{self.destino_name.get()}' no existe.\n"
                                         "Puede crearla con el botón 'Crear Base de Datos si No Existe'.")
                    return False
                
                conn = psycopg2.connect(
                    host=self.destino_host.get(),
                    port=self.destino_port.get(),
                    database=self.destino_name.get(),
                    user=self.destino_user.get(),
                    password=self.destino_password.get()
                )
                nombre_bd = self.destino_name.get()
            
            # Verificar si la tabla eventos existe
            cur = conn.cursor()
            cur.execute("SELECT to_regclass('public.eventos')")
            tabla_existe = cur.fetchone()[0]
            
            conn.close()
            
            if tabla_existe:
                messagebox.showinfo("Conexión Exitosa", 
                                  f"Conexión a {nombre_bd} establecida correctamente.\n"
                                  "La tabla 'eventos' existe.")
                self.agregar_log(f"Conexión a {nombre_bd} verificada: OK")
                return True
            else:
                messagebox.showwarning("Conexión Exitosa / Tabla No Existe", 
                                     f"Conexión a {nombre_bd} establecida correctamente.\n"
                                     "La tabla 'eventos' NO existe.")
                self.agregar_log(f"Conexión a {nombre_bd} verificada: OK, pero la tabla 'eventos' no existe")
                return False
            
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"Error al conectar a la base de datos:\n{e}")
            self.agregar_log(f"Error de conexión a {tipo}: {e}")
            return False
    
    def crear_bd_destino(self):
        """Crea la base de datos destino y su tabla eventos si no existen."""
        try:
            # Conectar a PostgreSQL (base postgres)
            conn_postgres = psycopg2.connect(
                host=self.destino_host.get(),
                port=self.destino_port.get(),
                database="postgres",
                user=self.destino_user.get(),
                password=self.destino_password.get()
            )
            conn_postgres.autocommit = True
            cur = conn_postgres.cursor()
            
            # Verificar si la BD existe
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.destino_name.get(),))
            exists = cur.fetchone()
            
            if not exists:
                # Crear la base de datos
                cur.execute(f"CREATE DATABASE {self.destino_name.get()}")
                self.agregar_log(f"Base de datos '{self.destino_name.get()}' creada.")
            else:
                self.agregar_log(f"La base de datos '{self.destino_name.get()}' ya existe.")
            
            conn_postgres.close()
            
            # Conectar a la BD destino
            conn_destino = psycopg2.connect(
                host=self.destino_host.get(),
                port=self.destino_port.get(),
                database=self.destino_name.get(),
                user=self.destino_user.get(),
                password=self.destino_password.get()
            )
            conn_destino.autocommit = True
            cur = conn_destino.cursor()
            
            # Verificar si la tabla eventos existe
            cur.execute("SELECT to_regclass('public.eventos')")
            tabla_existe = cur.fetchone()[0]
            
            if not tabla_existe:
                # Crear la tabla eventos
                cur.execute("""
                CREATE TABLE eventos (
                    id SERIAL PRIMARY KEY,
                    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ubicacion VARCHAR(100) NOT NULL,
                    tipo_evento VARCHAR(100) NOT NULL,
                    descripcion TEXT,
                    sensor VARCHAR(100) NOT NULL
                )
                """)
                self.agregar_log("Tabla 'eventos' creada.")
                
                # Insertar datos de ejemplo
                datos = [
                    ('Tokio', 'Sistema', 'Sistema de monitoreo iniciado', 'Arduino'),
                    ('Tokio', 'Temperatura', 'Temperatura registrada: 25.5 C', 'LM35'),
                    ('Tokio', 'Alerta Sismica', 'Se ha detectado actividad sismica. Mantenga la calma.', 'SW-18010P'),
                    ('Tokio', 'Incendio', 'Se ha detectado un posible incendio. Temperatura: 70.3 C', 'LM35'),
                    ('Cruce de Shibuya', 'Trafico Peatonal', 'Se ha detectado movimiento de peatones en el cruce.', 'PIR')
                ]
                
                for dato in datos:
                    cur.execute("""
                    INSERT INTO eventos (ubicacion, tipo_evento, descripcion, sensor)
                    VALUES (%s, %s, %s, %s)
                    """, dato)
                
                self.agregar_log("Datos de ejemplo insertados.")
            else:
                self.agregar_log("La tabla 'eventos' ya existe.")
            
            conn_destino.close()
            
            messagebox.showinfo("Base de Datos Preparada", 
                             f"La base de datos '{self.destino_name.get()}' está lista para usar.")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al crear la base de datos:\n{e}")
            self.agregar_log(f"Error: {e}")
            return False
    
    def guardar_configuracion(self):
        """Guarda la configuración en un archivo."""
        try:
            with open("config_adaptador_bd.py", "w") as f:
                f.write("# Configuración del Adaptador de Base de Datos\n")
                f.write("# Generado automáticamente\n")
                f.write(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("CONFIG = {\n")
                f.write("    # Configuración de BD origen\n")
                f.write(f"    'origen_host': '{self.origen_host.get()}',\n")
                f.write(f"    'origen_port': '{self.origen_port.get()}',\n")
                f.write(f"    'origen_name': '{self.origen_name.get()}',\n")
                f.write(f"    'origen_user': '{self.origen_user.get()}',\n")
                f.write(f"    'origen_password': '{self.origen_password.get()}',\n\n")
                
                f.write("    # Configuración de BD destino\n")
                f.write(f"    'destino_host': '{self.destino_host.get()}',\n")
                f.write(f"    'destino_port': '{self.destino_port.get()}',\n")
                f.write(f"    'destino_name': '{self.destino_name.get()}',\n")
                f.write(f"    'destino_user': '{self.destino_user.get()}',\n")
                f.write(f"    'destino_password': '{self.destino_password.get()}',\n\n")
                
                f.write("    # Configuración de sincronización\n")
                f.write(f"    'intervalo_sync': {self.intervalo_sync}\n")
                f.write("}\n")
            
            messagebox.showinfo("Configuración Guardada", 
                              "La configuración se ha guardado correctamente en 'config_adaptador_bd.py'")
            self.agregar_log("Configuración guardada en 'config_adaptador_bd.py'")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar la configuración:\n{e}")
            self.agregar_log(f"Error al guardar configuración: {e}")
            return False
    
    def iniciar_sincronizacion(self):
        """Inicia la sincronización automática."""
        if self.ejecutando:
            messagebox.showinfo("Ya en ejecución", "La sincronización ya está en ejecución.")
            return
        
        self.ejecutando = True
        self.agregar_log("Sincronización automática iniciada.")
        self.programar_sincronizacion()
    
    def detener_sincronizacion(self):
        """Detiene la sincronización automática."""
        if not self.ejecutando:
            messagebox.showinfo("No en ejecución", "La sincronización no está en ejecución.")
            return
        
        self.ejecutando = False
        self.agregar_log("Sincronización automática detenida.")
    
    def programar_sincronizacion(self):
        """Programa la próxima sincronización."""
        if not self.ejecutando:
            return
        
        self.sincronizar_ahora()
        self.root.after(self.intervalo_sync * 1000, self.programar_sincronizacion)
    
    def sincronizar_ahora(self):
        """Realiza la sincronización ahora."""
        try:
            # Conectar a la BD origen
            conn_origen = psycopg2.connect(
                host=self.origen_host.get(),
                port=self.origen_port.get(),
                database=self.origen_name.get(),
                user=self.origen_user.get(),
                password=self.origen_password.get()
            )
            
            # Conectar a la BD destino
            conn_destino = psycopg2.connect(
                host=self.destino_host.get(),
                port=self.destino_port.get(),
                database=self.destino_name.get(),
                user=self.destino_user.get(),
                password=self.destino_password.get()
            )
            
            # Obtener último ID sincronizado en destino
            cur_destino = conn_destino.cursor()
            cur_destino.execute("SELECT MAX(id) FROM eventos")
            resultado = cur_destino.fetchone()
            ultimo_id_destino = resultado[0] if resultado and resultado[0] else 0
            
            # Obtener eventos nuevos del origen
            cur_origen = conn_origen.cursor()
            cur_origen.execute("""
                SELECT id, fecha_hora, ubicacion, tipo_evento, descripcion, sensor
                FROM eventos
                WHERE id > %s
                ORDER BY id
            """, (self.ultimo_id_sincronizado,))
            
            eventos_nuevos = cur_origen.fetchall()
            
            if not eventos_nuevos:
                self.agregar_log("No hay nuevos eventos para sincronizar.")
                cur_origen.close()
                cur_destino.close()
                conn_origen.close()
                conn_destino.close()
                return
            
            # Sincronizar eventos
            contador = 0
            for evento in eventos_nuevos:
                id_origen, fecha_hora, ubicacion, tipo_evento, descripcion, sensor = evento
                
                # Insertar en destino
                cur_destino.execute("""
                    INSERT INTO eventos (fecha_hora, ubicacion, tipo_evento, descripcion, sensor)
                    VALUES (%s, %s, %s, %s, %s)
                """, (fecha_hora, ubicacion, tipo_evento, descripcion, sensor))
                
                contador += 1
                self.ultimo_id_sincronizado = id_origen
            
            # Confirmar cambios
            conn_destino.commit()
            
            self.agregar_log(f"Sincronización completada: {contador} eventos transferidos.")
            self.agregar_log(f"Último ID sincronizado: {self.ultimo_id_sincronizado}")
            
            # Cerrar conexiones
            cur_origen.close()
            cur_destino.close()
            conn_origen.close()
            conn_destino.close()
            
        except Exception as e:
            self.agregar_log(f"Error durante la sincronización: {e}")
    
    def salir(self):
        """Salir de la aplicación."""
        if self.ejecutando:
            respuesta = messagebox.askyesno("Confirmar", 
                                         "La sincronización está en ejecución.\n"
                                         "¿Desea detenerla y salir?")
            if not respuesta:
                return
            
            self.ejecutando = False
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = AdaptadorBD(root)
    root.mainloop()

if __name__ == "__main__":
    main()