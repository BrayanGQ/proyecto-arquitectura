import tkinter as tk
from tkinter import ttk, messagebox
from conexion import ConexionDB
import re
import time
import pygame
import threading
from datetime import datetime, timedelta
import os
import logging

# Configurar logging para registrar errores y eventos importantes
logging.basicConfig(
    filename='dashboard.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Dashboard de Monitoreo Arduino - Sistema Inteligente")
        self.root.state("zoomed")  # Pantalla completa (Windows)

        # Inicializar conexión a la base de datos
        self.db = ConexionDB()
        if not self.db.verificar_conexion():
            messagebox.showerror("Error de Conexión", 
                               "No se pudo conectar a la base de datos.\n"
                               "Verifique la configuración en conexion.py")
            logging.error("Falló la conexión inicial a la base de datos")
        else:
            logging.info("Conexión a la base de datos establecida correctamente")
        
        # Inicializar mixer para sonidos de alerta
        try:
            pygame.mixer.init()
            logging.info("Pygame mixer inicializado correctamente")
        except Exception as e:
            logging.error(f"Error al inicializar pygame: {e}")
            print(f"Error al inicializar pygame: {e}")
        
        # Variables de estado
        self.ultimo_evento_alertado = None  # Para evitar alertas repetidas
        self.id_ultimo_evento = None        # ID del último evento en la base de datos
        self.temperatura_actual = "--"
        self.alerta_actual = "Sin eventos recientes"
        
        # Crear interfaz de usuario
        self.crear_interfaz()
        
        # Cargar datos iniciales y configurar actualizaciones
        self.cargar_eventos()
        self.actualizar_info_ciudad()
        self.actualizar_datos()

    def crear_interfaz(self):
        # ========== Encabezado ==========
        encabezado = tk.Label(self.root, text="SISTEMA DE MONITOREO - EVENTOS EN VIVO",
                             font=("Helvetica", 22, "bold"), bg="#2c3e50", fg="white", pady=15)
        encabezado.pack(fill=tk.X)

        # ========== Marco de información actual ==========
        info_frame = tk.Frame(self.root, bg="#ecf0f1", pady=10)
        info_frame.pack(padx=20, pady=10, fill=tk.X)

        # Panel para mostrar la temperatura actual
        self.temperatura_label = tk.Label(info_frame, 
                                        text=f"Temperatura actual: {self.temperatura_actual} °C",
                                        font=("Arial", 16), fg="#2980b9", bg="#ecf0f1")
        self.temperatura_label.pack(anchor="w", padx=10, pady=5)

        # Panel para mostrar alertas activas
        self.alerta_label = tk.Label(info_frame, 
                                    text=f"Alerta: {self.alerta_actual}",
                                    font=("Arial", 16, "bold"), fg="#c0392b", bg="#ecf0f1")
        self.alerta_label.pack(anchor="w", padx=10, pady=5)

        # ========== Título de la tabla ==========
        titulo_eventos = tk.Label(self.root, text="Eventos recientes del sistema de monitoreo",
                                 font=("Arial", 18, "bold"), pady=10)
        titulo_eventos.pack()

        # ========== Filtros ==========
        filtro_frame = tk.Frame(self.root)
        filtro_frame.pack(pady=5)

        # Filtros por fecha
        tk.Label(filtro_frame, text="Año:", font=("Arial", 12)).grid(row=0, column=0, padx=5)
        self.anio_entry = tk.Entry(filtro_frame, width=6)
        self.anio_entry.grid(row=0, column=1, padx=5)

        tk.Label(filtro_frame, text="Mes:", font=("Arial", 12)).grid(row=0, column=2, padx=5)
        self.mes_entry = tk.Entry(filtro_frame, width=4)
        self.mes_entry.grid(row=0, column=3, padx=5)

        tk.Label(filtro_frame, text="Día:", font=("Arial", 12)).grid(row=0, column=4, padx=5)
        self.dia_entry = tk.Entry(filtro_frame, width=4)
        self.dia_entry.grid(row=0, column=5, padx=5)

        # Botones de filtro
        tk.Button(filtro_frame, text="Buscar", command=self.buscar_eventos,
                 font=("Arial", 10), bg="#3498db", fg="white").grid(row=0, column=6, padx=10)
        
        tk.Button(filtro_frame, text="Refrescar Tabla", command=self.cargar_eventos,
                 font=("Arial", 10), bg="#2ecc71", fg="white").grid(row=0, column=7, padx=5)
        
        # Filtro por tipo de evento
        tk.Label(filtro_frame, text="Tipo:", font=("Arial", 12)).grid(row=0, column=8, padx=5)
        self.tipo_combo = ttk.Combobox(filtro_frame, width=15, 
                                     values=["Todos", "Temperatura", "Alerta Sismica", "Incendio", "Trafico Peatonal"])
        self.tipo_combo.current(0)  # Seleccionar "Todos" por defecto
        self.tipo_combo.grid(row=0, column=9, padx=5)
        self.tipo_combo.bind("<<ComboboxSelected>>", self.filtrar_por_tipo)

        # ========== Tabla ==========
        tabla_frame = tk.LabelFrame(self.root, text="Eventos Registrados",
                                   font=("Arial", 12, "bold"), padx=10, pady=10)
        tabla_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Crear tabla con scrollbar
        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tabla_frame, 
            columns=("Fecha", "Ubicación", "Tipo", "Descripción"), 
            show="headings", 
            yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.tree.yview)
        
        # Configurar columnas
        self.tree.heading("Fecha", text="Fecha y Hora")
        self.tree.heading("Ubicación", text="Ubicación")
        self.tree.heading("Tipo", text="Tipo de Evento")
        self.tree.heading("Descripción", text="Descripción")
        
        # Ajustar ancho de columnas
        self.tree.column("Fecha", width=160, anchor=tk.CENTER)
        self.tree.column("Ubicación", width=150, anchor=tk.CENTER)
        self.tree.column("Tipo", width=150, anchor=tk.CENTER)
        self.tree.column("Descripción", width=400, anchor=tk.W)
        
        self.tree.pack(fill=tk.BOTH, expand=True)

        # ========== Barra de estado ==========
        self.barra_estado = tk.Label(self.root, text="Listo", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.barra_estado.pack(side=tk.BOTTOM, fill=tk.X)

    def cargar_eventos(self):
        """Carga los eventos más recientes en la tabla."""
        # Limpiar tabla
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            # Verificar conexión a la base de datos
            if not self.db.verificar_conexion():
                self.barra_estado.config(text="Error: No hay conexión a la base de datos. Intentando reconectar...")
                self.db = ConexionDB()  # Intentar reconexión
                if not self.db.verificar_conexion():
                    messagebox.showerror("Error de Conexión", "No se pudo reconectar a la base de datos.")
                    logging.error("Fallo en reconexión a la base de datos al cargar eventos")
                    return
                logging.info("Reconexión a la base de datos exitosa")

            # Obtener eventos y mostrarlos
            eventos = self.db.obtener_eventos()
            if not eventos:
                self.barra_estado.config(text="No se encontraron eventos en la base de datos.")
                return

            for ev in eventos:
                # Formatear fecha si es datetime
                fecha_formateada = ev[0]
                if isinstance(ev[0], datetime):
                    fecha_formateada = ev[0].strftime("%Y-%m-%d %H:%M:%S")
                
                self.tree.insert("", "end", values=(
                    fecha_formateada,
                    ev[1],
                    ev[2],
                    ev[3]
                ))
            
            # Actualizar barra de estado
            self.barra_estado.config(text=f"Se cargaron {len(eventos)} eventos.")
            logging.info(f"Se cargaron {len(eventos)} eventos exitosamente")
            
        except Exception as e:
            mensaje_error = f"Error al cargar eventos: {e}"
            self.barra_estado.config(text=mensaje_error[:50] + "...")
            logging.error(mensaje_error)
            print(mensaje_error)

    def buscar_eventos(self):
        """Busca eventos según los filtros de fecha ingresados."""
        # Obtener valores de los filtros
        anio = self.anio_entry.get()
        mes = self.mes_entry.get()
        dia = self.dia_entry.get()

        # Validar entradas
        try:
            anio = int(anio) if anio.strip() else None
            mes = int(mes) if mes.strip() else None
            dia = int(dia) if dia.strip() else None
            
            if mes and (mes < 1 or mes > 12):
                raise ValueError("El mes debe estar entre 1 y 12")
            if dia and (dia < 1 or dia > 31):
                raise ValueError("El día debe estar entre 1 y 31")
                
        except ValueError as e:
            messagebox.showerror("Error en el filtro", f"Error en los valores de fecha: {e}")
            logging.error(f"Error en filtro de fecha: {e}")
            return

        try:
            # Verificar conexión a la base de datos
            if not self.db.verificar_conexion():
                self.barra_estado.config(text="Error: No hay conexión a la base de datos. Intentando reconectar...")
                self.db = ConexionDB()  # Intentar reconexión
                if not self.db.verificar_conexion():
                    messagebox.showerror("Error de Conexión", "No se pudo reconectar a la base de datos.")
                    logging.error("Fallo en reconexión a la base de datos al buscar eventos")
                    return
                logging.info("Reconexión a la base de datos exitosa")

            # Obtener eventos filtrados
            eventos = self.db.obtener_eventos_filtrados(anio, mes, dia)

            # Limpiar tabla
            for i in self.tree.get_children():
                self.tree.delete(i)

            # Verificar si hay resultados
            if not eventos:
                messagebox.showinfo("Sin resultados", "No se encontraron eventos con los filtros aplicados.")
                self.barra_estado.config(text="La búsqueda no produjo resultados.")
                return

            # Mostrar resultados
            for ev in eventos:
                # Formatear fecha si es datetime
                fecha_formateada = ev[0]
                if isinstance(ev[0], datetime):
                    fecha_formateada = ev[0].strftime("%Y-%m-%d %H:%M:%S")
                    
                self.tree.insert("", "end", values=(
                    fecha_formateada,
                    ev[1],
                    ev[2],
                    ev[3]
                ))
            
            # Actualizar barra de estado
            self.barra_estado.config(text=f"Se encontraron {len(eventos)} eventos con los filtros aplicados.")
            logging.info(f"Búsqueda exitosa: {len(eventos)} eventos encontrados con filtros: año={anio}, mes={mes}, día={dia}")
            
        except Exception as e:
            mensaje_error = f"Error al buscar eventos: {e}"
            self.barra_estado.config(text=mensaje_error[:50] + "...")
            logging.error(mensaje_error)
            print(mensaje_error)

    def filtrar_por_tipo(self, event=None):
        """Filtra eventos por tipo seleccionado en el combobox."""
        tipo_seleccionado = self.tipo_combo.get()
        
        try:
            # Verificar conexión a la base de datos
            if not self.db.verificar_conexion():
                self.barra_estado.config(text="Error: No hay conexión a la base de datos. Intentando reconectar...")
                self.db = ConexionDB()  # Intentar reconexión
                if not self.db.verificar_conexion():
                    messagebox.showerror("Error de Conexión", "No se pudo reconectar a la base de datos.")
                    logging.error("Fallo en reconexión a la base de datos al filtrar por tipo")
                    return
                logging.info("Reconexión a la base de datos exitosa")
            
            if tipo_seleccionado == "Todos":
                # Cargar todos los eventos
                self.cargar_eventos()
                return
            
            # Usar el método de la conexión para obtener eventos por tipo
            eventos = self.db.obtener_eventos_por_tipo(tipo_seleccionado)
            
            # Limpiar tabla
            for i in self.tree.get_children():
                self.tree.delete(i)
            
            if not eventos:
                messagebox.showinfo("Sin resultados", f"No hay eventos del tipo '{tipo_seleccionado}'.")
                self.barra_estado.config(text=f"No se encontraron eventos del tipo '{tipo_seleccionado}'.")
                return
            
            # Mostrar resultados
            for ev in eventos:
                # Formatear fecha si es datetime
                fecha_formateada = ev[0]
                if isinstance(ev[0], datetime):
                    fecha_formateada = ev[0].strftime("%Y-%m-%d %H:%M:%S")
                
                self.tree.insert("", "end", values=(
                    fecha_formateada,
                    ev[1],
                    ev[2],
                    ev[3]
                ))
            
            # Actualizar barra de estado
            self.barra_estado.config(text=f"Se encontraron {len(eventos)} eventos del tipo '{tipo_seleccionado}'.")
            logging.info(f"Filtro por tipo exitoso: {len(eventos)} eventos del tipo '{tipo_seleccionado}'")
            
        except Exception as e:
            mensaje_error = f"Error al filtrar por tipo: {e}"
            self.barra_estado.config(text=mensaje_error[:50] + "...")
            logging.error(mensaje_error)
            print(mensaje_error)

    def actualizar_info_ciudad(self):
        """Actualiza la información de temperatura."""
        try:
            ultimo_temp = self.db.obtener_ultimo_evento_por_tipo("Temperatura")
            if ultimo_temp:
                _, _, _, descripcion = ultimo_temp
                match = re.search(r'([0-9]+(?:\.[0-9]+)?)', descripcion)
                if match:
                    self.temperatura_actual = match.group(1)
                    self.temperatura_label.config(
                        text=f"Temperatura actual: {self.temperatura_actual} °C",
                        fg="#2980b9"
                    )
                else:
                    self.temperatura_actual = "--"
                    self.temperatura_label.config(
                        text="Temperatura actual: No disponible",
                        fg="#7f8c8d"
                    )
            else:
                self.temperatura_actual = "--"
                self.temperatura_label.config(
                    text="Temperatura actual: -- °C",
                    fg="#7f8c8d"
                )
        except Exception as e:
            mensaje_error = f"Error al actualizar información de temperatura: {e}"
            logging.error(mensaje_error)
            print(mensaje_error)
            self.temperatura_actual = "--"
            self.temperatura_label.config(
                text="Temperatura actual: Error de conexión",
                fg="#e74c3c"  # Rojo para indicar error
            )

    def obtener_id_ultimo_evento(self):
        """Obtiene el ID del último evento insertado en la base de datos."""
        try:
            ultimo_id = self.db.obtener_ultimo_id()
            return ultimo_id
        except Exception as e:
            logging.error(f"Error al obtener último ID: {e}")
            return None

    def actualizar_alerta(self):
        """
        Actualiza la alerta mostrada y verifica si hay nuevas alertas.
        Solo muestra alertas de eventos que ACABAN de ocurrir (nuevo ID).
        """
        try:
            # Obtener el ID del último evento en la base de datos
            nuevo_id = self.obtener_id_ultimo_evento()
            
            # Si no hay eventos en la BD o no podemos obtener el ID
            if not nuevo_id:
                self.alerta_actual = "Sin eventos recientes"
                self.alerta_label.config(
                    text="Alerta: Sin eventos recientes",
                    fg="#2ecc71"  # Verde para estado normal
                )
                return
                
            # Verificar si es un evento nuevo (comparando con el último ID que procesamos)
            if nuevo_id != self.id_ultimo_evento:
                # Actualizar nuestro ID almacenado
                evento_anterior = self.id_ultimo_evento
                self.id_ultimo_evento = nuevo_id
                
                # Obtener el último evento para saber qué tipo es
                ultimo_evento = self.db.obtener_evento_por_id(nuevo_id)
                
                if not ultimo_evento:
                    return
                    
                fecha_hora, ubicacion, tipo_evento, descripcion = ultimo_evento
                
                # Actualizar la etiqueta de alerta con este evento
                if tipo_evento in ['Alerta Sismica', 'Incendio']:
                    # Formatear fecha
                    fecha_formateada = fecha_hora
                    if isinstance(fecha_hora, datetime):
                        fecha_formateada = fecha_hora.strftime("%H:%M:%S")
                    
                    # Actualizar texto de alerta con hora
                    self.alerta_actual = f"{tipo_evento} - {descripcion} ({fecha_formateada})"
                    self.alerta_label.config(
                        text=f"Alerta: {self.alerta_actual}",
                        fg="#c0392b"  # Rojo para alertas
                    )
                    
                    # Mostrar alerta emergente SOLO si es un evento nuevo 
                    # y es un evento crítico (alerta o incendio)
                    # y no es el evento inicial al arrancar (evento_anterior es None)
                    if evento_anterior is not None:
                        print(f"Nuevo evento crítico detectado: {tipo_evento}")
                        self.alerta_emergencia(tipo_evento, descripcion)
                
                # Si es un evento de temperatura pero hay alerta activa, mantener la alerta
                elif (tipo_evento == 'Temperatura' and
                      ('Alerta Sismica' in self.alerta_actual or 'Incendio' in self.alerta_actual)):
                    # Mantener el mensaje de alerta anterior, no actualizamos nada
                    pass
                else:
                    # No es un evento crítico, mostrar estado normal
                    self.alerta_actual = "Sistema operando normalmente"
                    self.alerta_label.config(
                        text=f"Alerta: {self.alerta_actual}",
                        fg="#2ecc71"  # Verde para estado normal
                    )
            
        except Exception as e:
            mensaje_error = f"Error al actualizar alertas: {e}"
            logging.error(mensaje_error)
            print(mensaje_error)
            self.alerta_label.config(
                text="Alerta: Error de conexión",
                fg="#e74c3c"  # Rojo para indicar error
            )

    def actualizar_datos(self):
        """Actualiza los datos del dashboard periódicamente."""
        try:
            self.actualizar_info_ciudad()
            self.actualizar_alerta()
            
            # Si hay pocos elementos en la tabla, refrescar datos completos
            if len(self.tree.get_children()) < 10:
                self.cargar_eventos()
                
        except Exception as e:
            mensaje_error = f"Error al actualizar datos: {e}"
            logging.error(mensaje_error)
            print(mensaje_error)
            # No mostrar messagebox aquí para no interrumpir al usuario
            self.barra_estado.config(text=f"Error: {str(e)[:50]}...")
        
        # Programar siguiente actualización - aumentado a 2 segundos para reducir carga
        self.root.after(2000, self.actualizar_datos)
    
    def reproducir_sonido(self):
        """Reproduce un sonido de alerta."""
        try:
            print("Intentando reproducir sonido de alerta...")
            # Inicializar pygame.mixer si no se ha hecho ya
            if not pygame.mixer.get_init():
                pygame.mixer.init()
                print("Pygame mixer inicializado en reproducir_sonido")
                
            # Rutas de sonido a probar en orden
            rutas_a_probar = [
                # Ruta específica proporcionada
                r"C:\Users\braya\Desktop\proyecto arquitectura dashboard\proyecto arquitectura\recursos\sonido\random-alarm-319318.mp3",
                # Otras rutas posibles
                "alerta.mp3",
                "recursos/sonido/alerta.mp3",
                "recursos/sonido/random-alarm-319318.mp3",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "alerta.mp3"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "recursos/sonido/alerta.mp3"),
                # Rutas absolutas de respaldo
                r"C:\Windows\Media\Alarm01.wav",  # Sonido estándar de Windows
                r"C:\Windows\Media\Windows Exclamation.wav"
            ]
            
            # Intentar cada ruta hasta encontrar una que funcione
            for ruta in rutas_a_probar:
                print(f"Probando sonido en: {ruta}")
                if os.path.exists(ruta):
                    print(f"¡Archivo encontrado! Cargando: {ruta}")
                    try:
                        pygame.mixer.music.load(ruta)
                        pygame.mixer.music.set_volume(1.0)  # Volumen máximo
                        pygame.mixer.music.play()
                        print(f"¡Sonido reproduciendo desde {ruta}!")
                        logging.info(f"Reproduciendo sonido de alarma desde: {ruta}")
                        return True
                    except Exception as e:
                        print(f"Error al cargar/reproducir {ruta}: {e}")
                        logging.error(f"Error al cargar/reproducir {ruta}: {e}")
                        continue  # Probar con la siguiente ruta
            
            # Si llegamos aquí, no se encontró ningún archivo de sonido o hubo errores
            print("No se pudo reproducir ningún sonido de alarma, intentando beep...")
            logging.warning("No se pudo reproducir ningún sonido de alarma")
            
            # Intentar usar beep del sistema como último recurso
            try:
                import winsound
                for _ in range(3):  # Emitir 3 beeps para mayor llamada de atención
                    winsound.Beep(800, 300)  # Frecuencia más baja, duración más corta
                    time.sleep(0.2)
                    winsound.Beep(1000, 500)  # Frecuencia más alta, duración más larga
                    time.sleep(0.2)
                logging.info("Se usó beep del sistema como alternativa")
                print("Beep del sistema reproducido con éxito")
                return True
            except Exception as e:
                print(f"Error en beep: {e}")
                logging.error(f"No se pudo usar beep del sistema: {e}")
            return False
                
        except Exception as e:
            mensaje_error = f"Error al reproducir sonido: {e}"
            logging.error(mensaje_error)
            print(mensaje_error)
            return False
    
    def alerta_emergencia(self, tipo_evento, descripcion):
        """Muestra un diálogo de alerta animado y reproduce un sonido de emergencia."""
        print(f"ALERTA DETECTADA: {tipo_evento} - {descripcion}")
        logging.info(f"Alerta de emergencia: {tipo_evento} - {descripcion}")
        
        # Reproducir sonido en un hilo separado
        def reproducir_en_hilo():
            try:
                exito = self.reproducir_sonido()
                # Si el sonido se reprodujo correctamente, detenerlo después de 9 segundos
                if exito:
                    print("Sonido reproducido, durará 9 segundos")
                    time.sleep(9)  # Reproduce el sonido por 9 segundos
                    pygame.mixer.music.stop()
                    print("Sonido detenido después de 9 segundos")
            except Exception as e:
                print(f"Error en hilo de reproducción de sonido: {e}")
                logging.error(f"Error en hilo de reproducción de sonido: {e}")
        
        # Crear una ventana de alerta personalizada con animación
        def mostrar_alerta_animada():
            try:
                print("Creando ventana de alerta emergente...")
                # Crear una ventana flotante para la alerta
                alerta_window = tk.Toplevel(self.root)
                alerta_window.title("¡¡ALERTA DE EMERGENCIA!!")
                
                # Asegurar que la ventana tiene el foco
                alerta_window.focus_force()
                alerta_window.grab_set()  # Hacer modal
                
                # Configurar geometría de la ventana
                ancho_ventana = 500
                alto_ventana = 300
                
                # Centrar la ventana en la pantalla
                pos_x = alerta_window.winfo_screenwidth() // 2 - ancho_ventana // 2
                pos_y = alerta_window.winfo_screenheight() // 2 - alto_ventana // 2
                alerta_window.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")
                
                # Configurar el fondo en color de alerta
                alerta_window.configure(bg="#ff0000")  # Rojo más intenso
                
                # Hacer que la ventana siempre esté encima
                alerta_window.attributes("-topmost", True)
                
                # Icono de advertencia
                icono_frame = tk.Frame(alerta_window, bg="#ff0000")
                icono_frame.pack(pady=10)
                
                # Se puede usar un emoji como alternativa a una imagen
                icono_label = tk.Label(icono_frame, text="⚠️", font=("Arial", 48), bg="#ff0000", fg="black")
                icono_label.pack()
                
                # Marco para el texto de la alerta
                texto_frame = tk.Frame(alerta_window, bg="#ff0000")
                texto_frame.pack(expand=True, fill=tk.BOTH, padx=20)
                
                # Título de la alerta
                titulo_label = tk.Label(texto_frame, 
                                       text=f"¡ALERTA: {tipo_evento.upper()}!", 
                                       font=("Arial", 24, "bold"),
                                       fg="white", bg="#ff0000")
                titulo_label.pack(pady=10)
                
                # Descripción de la alerta
                desc_label = tk.Label(texto_frame, 
                                     text=descripcion, 
                                     font=("Arial", 14),
                                     fg="white", bg="#ff0000",
                                     wraplength=450)  # Ajustar el texto si es muy largo
                desc_label.pack(pady=10)
                
                # Instrucciones
                instruccion_label = tk.Label(texto_frame,
                                           text="Se recomienda seguir los protocolos de seguridad establecidos.",
                                           font=("Arial", 12, "italic"),
                                           fg="white", bg="#ff0000",
                                           wraplength=450)
                instruccion_label.pack(pady=10)
                
                # Variable para cambiar entre colores
                es_rojo = [False]  # Usar lista para que pueda ser modificada en la función interna
                
                # Función para cambiar el color del texto intermitentemente
                def cambiar_color():
                    if alerta_window.winfo_exists():  # Verificar que la ventana siga existiendo
                        if es_rojo[0]:
                            titulo_label.config(fg="white")
                            es_rojo[0] = False
                        else:
                            titulo_label.config(fg="yellow")
                            es_rojo[0] = True
                        
                        # Programar el próximo cambio de color (cada 500ms)
                        alerta_window.after(500, cambiar_color)
                
                # Iniciar la animación de cambio de color
                cambiar_color()
                
                # Función para hacer "parpadear" la ventana
                def flash_window():
                    if alerta_window.winfo_exists():  # Verificar que la ventana siga existiendo
                        # Alternar entre dos colores de fondo
                        current_bg = alerta_window.cget("bg")
                        if current_bg == "#ff0000":  # Si es rojo
                            alerta_window.configure(bg="#ff8080")  # Cambiar a un rojo más claro
                            icono_frame.configure(bg="#ff8080")
                            texto_frame.configure(bg="#ff8080")
                            icono_label.configure(bg="#ff8080")
                        else:
                            alerta_window.configure(bg="#ff0000")  # Cambiar a rojo
                            icono_frame.configure(bg="#ff0000")
                            texto_frame.configure(bg="#ff0000")
                            icono_label.configure(bg="#ff0000")
                        
                        # Programar el próximo cambio (cada 750ms)
                        alerta_window.after(750, flash_window)
                
                # Iniciar el parpadeo de la ventana
                flash_window()
                
                # Cerrar automáticamente la ventana después de 9 segundos
                alerta_window.after(9000, alerta_window.destroy)
                
                print("Ventana de alerta creada exitosamente")
                
            except Exception as e:
                print(f"Error al mostrar alerta animada: {e}")
                logging.error(f"Error al mostrar alerta animada: {e}")
                # Mostrar messagebox tradicional como respaldo
                messagebox.showwarning("⚠ ALERTA DE EMERGENCIA", 
                                      f"Se ha detectado: {tipo_evento}\n\n{descripcion}")
        
        # Ejecutar estas funciones directamente, sin usar hilos
        # Los hilos pueden estar causando problemas
        mostrar_alerta_animada()
        
        # Iniciar el sonido en un hilo separado
        threading.Thread(target=reproducir_en_hilo, daemon=True).start()

    def reconectar_bd(self):
        """Intenta reconectar a la base de datos."""
        intentos = 0
        max_intentos = 3
        
        while intentos < max_intentos:
            try:
                self.db = ConexionDB()
                if self.db.verificar_conexion():
                    self.barra_estado.config(text="Reconexión exitosa a la base de datos.")
                    logging.info("Reconexión a la base de datos exitosa")
                    return True
                time.sleep(2)  # Esperar antes de reintentar
            except Exception as e:
                mensaje_error = f"Error al reconectar: {e}"
                logging.error(mensaje_error)
                print(mensaje_error)
            
            intentos += 1
        
        self.barra_estado.config(text="No se pudo reconectar a la base de datos después de varios intentos.")
        logging.error("Fallaron todos los intentos de reconexión")
        return False

# Código principal para iniciar la aplicación directamente (para pruebas)
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = Dashboard(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Error crítico que causó cierre de la aplicación: {e}")
        print(f"Error crítico: {e}")
        messagebox.showerror("Error Fatal", f"La aplicación se cerrará debido a un error crítico:\n{e}")