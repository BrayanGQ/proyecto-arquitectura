import serial
import time
import psycopg2
from datetime import datetime

# Configuración
CONFIG = {
    # Configuración del puerto serial
    'puerto_com': 'COM3',
    'baudrate': 9600,
    
    # Configuración de la base de datos
    'db_host': 'proyecto-universidad-instance-1.cla848gew495.us-east-2.rds.amazonaws.com',
    'db_port': '5432',
    'db_name': 'arduino_monitoreo',
    'db_user': 'postgres',
    'db_password': 'Matematicas123890',
    
    # Umbrales para alertas
    'umbral_temperatura_alta': 70.0,
    'umbral_vibracion': 900,
    
    # Intervalos para evitar duplicados (en segundos)
    'intervalo_temperatura': 30,
    'intervalo_terremoto': 60,
    'intervalo_incendio': 60,
    'intervalo_peatones': 10,
    
    # Duración de eventos críticos (en segundos)
    'duracion_evento_peatones': 15,  # 15 segundos sin registrar temperatura después de detectar peatones
    'duracion_evento_terremoto': 30, # 30 segundos sin registrar temperatura después de detectar terremoto
    'duracion_evento_incendio': 30,  # 30 segundos sin registrar temperatura después de detectar incendio
}

class MonitorArduino:
    def __init__(self, config=CONFIG):
        self.config = config
        self.conn = None
        self.ser = None
        
        # Variables para evitar duplicados
        self.ultima_temp = None
        self.ultima_temp_tiempo = 0
        self.ultima_alerta_terremoto = 0
        self.ultima_alerta_incendio = 0
        self.ultima_alerta_peatones = 0
        
        # Eventos activos - un sistema de prioridades
        self.evento_peatones_activo_hasta = 0
        self.evento_terremoto_activo_hasta = 0
        self.evento_incendio_activo_hasta = 0
        
        # Registros internos para depuración
        self.registros = []
    
    def _sanitizar_texto(self, texto):
        """Reemplaza caracteres problemáticos por versiones sin acentos."""
        if not isinstance(texto, str):
            return texto
            
        reemplazos = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U'
        }
        
        for original, reemplazo in reemplazos.items():
            texto = texto.replace(original, reemplazo)
        
        return texto
    
    def hay_evento_critico_activo(self):
        """Verifica si hay algún evento crítico activo actualmente."""
        tiempo_actual = time.time()
        return (tiempo_actual < self.evento_peatones_activo_hasta or
                tiempo_actual < self.evento_terremoto_activo_hasta or
                tiempo_actual < self.evento_incendio_activo_hasta)
    
    def conectar_bd(self):
        """Establece conexión con la base de datos PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                host=self.config['db_host'],
                port=self.config['db_port'],
                dbname=self.config['db_name'],
                user=self.config['db_user'],
                password=self.config['db_password'],
                client_encoding='latin1'
            )
            print(f"Conexión exitosa a la base de datos {self.config['db_name']}")
            return True
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            self.conn = None
            return False
    
    def conectar_arduino(self):
        """Establece conexión con el Arduino por puerto serial."""
        try:
            self.ser = serial.Serial(
                self.config['puerto_com'], 
                self.config['baudrate'], 
                timeout=1
            )
            print(f"Conexión exitosa al puerto {self.config['puerto_com']}")
            return True
        except Exception as e:
            print(f"Error al conectar al Arduino: {e}")
            self.ser = None
            return False
    
    def insertar_evento(self, ubicacion, tipo_evento, descripcion, sensor):
        """Inserta un evento en la base de datos."""
        if not self.conn:
            print("Error: No hay conexión a la base de datos")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Sanitizar datos para evitar problemas de codificación
            ubicacion = self._sanitizar_texto(ubicacion)
            tipo_evento = self._sanitizar_texto(tipo_evento)
            descripcion = self._sanitizar_texto(descripcion)
            sensor = self._sanitizar_texto(sensor)
            
            # Preparar y ejecutar la consulta
            query = """
                INSERT INTO eventos 
                    (ubicacion, tipo_evento, descripcion, sensor) 
                VALUES 
                    (%s, %s, %s, %s)
                RETURNING id;
            """
            cursor.execute(query, (ubicacion, tipo_evento, descripcion, sensor))
            
            # Obtener el ID del evento insertado
            evento_id = cursor.fetchone()[0]
            
            self.conn.commit()
            cursor.close()
            
            # Guardar registro local para depuración
            self.registros.append({
                'id': evento_id,
                'fecha': datetime.now(),
                'tipo': tipo_evento,
                'descripcion': descripcion
            })
            
            print(f"Evento registrado: ({evento_id}) {tipo_evento} - {descripcion}")
            return True
            
        except Exception as e:
            print(f"Error al insertar evento: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def iniciar_monitoreo(self):
        """Inicia el monitoreo de datos del Arduino."""
        # Verificar conexiones
        if not self.conn and not self.conectar_bd():
            print("No se pudo conectar a la base de datos. Abortando.")
            return False
        
        if not self.ser and not self.conectar_arduino():
            print("No se pudo conectar al Arduino. Abortando.")
            return False
        
        # Registrar inicio del sistema
        self.insertar_evento("Tokio", "Sistema", "Sistema de monitoreo iniciado", "Arduino")
        
        try:
            print("=== Monitoreo iniciado. Presiona Ctrl+C para detener ===")
            print("Cuando se detecten peatones, terremotos o incendios, se suspenderá el registro de temperatura.")
            
            # Mensaje EXACTO para la detección de peatones
            MENSAJE_PEATONES = "Sensor de movimiento: ACTIVADO"
            
            while True:
                if self.ser.in_waiting > 0:
                    try:
                        # Leer línea del Arduino
                        linea = self.ser.readline().decode('latin1', errors='replace').strip()
                        if not linea:
                            continue
                        
                        # Mostrar mensaje recibido
                        print(f"Recibido: {linea}")
                        
                        # Ver si hay algún evento crítico activo
                        evento_critico_activo = self.hay_evento_critico_activo()
                        tiempo_actual = time.time()
                        
                        # ===== PROCESAR TEMPERATURA (solo si no hay eventos críticos activos) =====
                        if ("Temperatura actual:" in linea or "DEBUG Temperatura:" in linea) and not evento_critico_activo:
                            try:
                                if "Temperatura actual:" in linea:
                                    partes = linea.split(":")
                                    if len(partes) >= 2:
                                        temp_str = partes[1].strip().split()[0]
                                        temp_valor = float(temp_str)
                                        self.registrar_temperatura(temp_valor)
                                elif "DEBUG Temperatura:" in linea:
                                    partes = linea.split(":")
                                    if len(partes) >= 2:
                                        temp_valor = float(partes[1].strip())
                                        self.registrar_temperatura(temp_valor)
                            except ValueError as e:
                                print(f"Error al convertir temperatura: {e}")
                            
                        # ===== PROCESAR VIBRACIÓN =====
                        elif "Sensor de vibracion:" in linea or "Sensor de vibración:" in linea:
                            if "ACTIVADO" in linea:
                                # Extraer valor del sensor
                                try:
                                    if "Valor:" in linea:
                                        valor_str = linea.split("Valor:")[1].split(")")[0].strip()
                                        valor = int(valor_str)
                                        self.procesar_vibracion(valor)
                                except (ValueError, IndexError) as e:
                                    print(f"Error al procesar vibración: {e}")
                        
                        # ===== PROCESAR ALERTA DE TERREMOTO =====
                        elif "ALERTA: Terremoto detectado!" in linea:
                            if tiempo_actual - self.ultima_alerta_terremoto >= self.config['intervalo_terremoto']:
                                descripcion = "Se ha detectado actividad sismica. Mantenga la calma y siga los protocolos de seguridad."
                                self.insertar_evento("Tokio", "Alerta Sismica", descripcion, "SW-18010P")
                                self.ultima_alerta_terremoto = tiempo_actual
                                
                                # Activar evento crítico de terremoto
                                self.evento_terremoto_activo_hasta = tiempo_actual + self.config['duracion_evento_terremoto']
                                print(f"=== EVENTO DE TERREMOTO ACTIVO - Suspendiendo registro de temperatura por {self.config['duracion_evento_terremoto']} segundos ===")
                        
                        # ===== PROCESAR ALERTA DE INCENDIO =====
                        elif "ALERTA: Incendio detectado!" in linea:
                            if tiempo_actual - self.ultima_alerta_incendio >= self.config['intervalo_incendio']:
                                if "Temperatura:" in linea:
                                    try:
                                        temp_str = linea.split("Temperatura:")[1].strip()
                                        temp_valor = float(temp_str.split()[0])
                                        descripcion = f"Se ha detectado un posible incendio. Temperatura: {temp_valor} C"
                                    except:
                                        descripcion = "Se ha detectado un posible incendio. Siga los protocolos de evacuacion."
                                else:
                                    descripcion = "Se ha detectado un posible incendio. Siga los protocolos de evacuacion."
                                
                                self.insertar_evento("Tokio", "Incendio", descripcion, "LM35")
                                self.ultima_alerta_incendio = tiempo_actual
                                
                                # Activar evento crítico de incendio
                                self.evento_incendio_activo_hasta = tiempo_actual + self.config['duracion_evento_incendio']
                                print(f"=== EVENTO DE INCENDIO ACTIVO - Suspendiendo registro de temperatura por {self.config['duracion_evento_incendio']} segundos ===")
                        
                        # ===== PROCESAR DETECCIÓN DE PEATONES =====
                        elif MENSAJE_PEATONES in linea:
                            # Procesar cuando recibimos "Sensor de movimiento: ACTIVADO"
                            if tiempo_actual - self.ultima_alerta_peatones >= self.config['intervalo_peatones']:
                                print("=== DETECTADO SENSOR DE MOVIMIENTO ACTIVADO - REGISTRANDO EN BD ===")
                                descripcion = "Se ha detectado movimiento de peatones en el cruce."
                                self.insertar_evento("Cruce de Shibuya", "Trafico Peatonal", descripcion, "PIR")
                                self.ultima_alerta_peatones = tiempo_actual
                                
                                # Activar evento crítico de peatones
                                self.evento_peatones_activo_hasta = tiempo_actual + self.config['duracion_evento_peatones']
                                print(f"=== EVENTO DE PEATONES ACTIVO - Suspendiendo registro de temperatura por {self.config['duracion_evento_peatones']} segundos ===")
                                
                    except Exception as e:
                        print(f"Error al procesar línea: {e}")
                
                time.sleep(0.1)  # Pequeña pausa para no saturar CPU
                
        except KeyboardInterrupt:
            print("\nMonitoreo detenido por el usuario")
        except Exception as e:
            print(f"Error en el monitoreo: {e}")
        finally:
            # Cerrar conexiones
            if self.ser:
                self.ser.close()
                print("Conexión serial cerrada")
            
            if self.conn:
                self.conn.close()
                print("Conexión a base de datos cerrada")
            
            print("Monitoreo finalizado")
    
    def registrar_temperatura(self, temperatura):
        """Procesa y registra un valor de temperatura."""
        tiempo_actual = time.time()
        
        # Verificar si debemos registrar esta temperatura
        if (self.ultima_temp is None or 
            abs(temperatura - self.ultima_temp) >= 1.0 or 
            tiempo_actual - self.ultima_temp_tiempo >= self.config['intervalo_temperatura']):
            
            # Registrar temperatura normal
            descripcion = f"Temperatura registrada: {temperatura} C"
            self.insertar_evento("Tokio", "Temperatura", descripcion, "LM35")
            
            # Verificar si es una temperatura alta (posible incendio)
            if (temperatura > self.config['umbral_temperatura_alta'] and 
                tiempo_actual - self.ultima_alerta_incendio >= self.config['intervalo_incendio']):
                
                descripcion = f"Se ha detectado un posible incendio. Temperatura: {temperatura} C"
                self.insertar_evento("Tokio", "Incendio", descripcion, "LM35")
                self.ultima_alerta_incendio = tiempo_actual
                
                # Activar evento crítico de incendio
                self.evento_incendio_activo_hasta = tiempo_actual + self.config['duracion_evento_incendio']
                print(f"=== EVENTO DE INCENDIO ACTIVO (por temperatura alta) - Suspendiendo registro de temperatura por {self.config['duracion_evento_incendio']} segundos ===")
            
            # Actualizar valores para evitar duplicados
            self.ultima_temp = temperatura
            self.ultima_temp_tiempo = tiempo_actual
    
    def procesar_vibracion(self, valor):
        """Procesa y registra datos de vibración."""
        tiempo_actual = time.time()
        
        # Si la vibración supera el umbral, registrar alerta de terremoto
        if valor > self.config['umbral_vibracion'] and tiempo_actual - self.ultima_alerta_terremoto >= self.config['intervalo_terremoto']:
            descripcion = f"Se ha detectado actividad sismica. Intensidad: {valor}. Mantenga la calma y siga los protocolos de seguridad."
            self.insertar_evento("Tokio", "Alerta Sismica", descripcion, "SW-18010P")
            self.ultima_alerta_terremoto = tiempo_actual
            
            # Activar evento crítico de terremoto
            self.evento_terremoto_activo_hasta = tiempo_actual + self.config['duracion_evento_terremoto']
            print(f"=== EVENTO DE TERREMOTO ACTIVO (por vibración) - Suspendiendo registro de temperatura por {self.config['duracion_evento_terremoto']} segundos ===")
    
    def obtener_registros(self):
        """Devuelve los registros locales de eventos para depuración."""
        return self.registros

# Función principal para ejecutar el monitor
def main():
    print("=== Monitor de Sensores Arduino ===")
    print(f"Este programa captura datos del puerto {CONFIG['puerto_com']} y los registra en la base de datos.")
    print("Los datos se insertarán en la tabla 'eventos' con la estructura compatible.")
    print()
    
    monitor = MonitorArduino()
    monitor.iniciar_monitoreo()

if __name__ == "__main__":
    main()