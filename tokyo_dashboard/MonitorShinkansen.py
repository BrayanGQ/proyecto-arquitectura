import serial
import time
import psycopg2
from datetime import datetime
import json

# Configuración específica para el Arduino Shinkansen
CONFIG_SHINKANSEN = {
    # Configuración del puerto serial
    'puerto_com': 'COM4',
    'baudrate': 9600,
    
    # Configuración de la base de datos
    'db_host': 'proyecto-universidad-instance-1.cla848gew495.us-east-2.rds.amazonaws.com',
    'db_port': '5432',
    'db_name': 'arduino_monitoreo',
    'db_user': 'postgres',
    'db_password': 'Matematicas123890',
    
    # Intervalos para evitar duplicados (en segundos)
    'intervalo_tren_llegada': 15,    # 15 segundos entre detecciones de tren
    'intervalo_puerta': 3,           # 3 segundos entre eventos de puerta
    'intervalo_ascensor': 5,         # 5 segundos entre eventos de ascensor
    
    # Configuración de detección
    'detectar_por_movimiento_pir': True,    # Detectar tren por PIR
    'detectar_por_ascensores': False,       # Detectar "llegada" por ascensores activos
}

class MonitorShinkansen:
    def __init__(self, config=CONFIG_SHINKANSEN):
        self.config = config
        self.conn = None
        self.ser = None
        
        # Variables para evitar duplicados
        self.ultima_llegada_tren = 0
        self.ultima_puerta_evento = 0
        self.ultimo_ascensor_evento = 0
        
        # Control de estado
        self.tren_en_estacion = False
        self.puerta_abierta = False
        
        # Registros internos para depuración
        self.registros = []
        
        # Contadores de ascensores activos
        self.ascensores_activos = 0
    
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
            print(f"🚆 Conexión exitosa a la base de datos {self.config['db_name']} (Shinkansen)")
            return True
        except Exception as e:
            print(f"❌ Error al conectar a la base de datos: {e}")
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
            print(f"🔌 Conexión exitosa al puerto {self.config['puerto_com']} (Arduino Shinkansen)")
            return True
        except Exception as e:
            print(f"❌ Error al conectar al Arduino Shinkansen: {e}")
            self.ser = None
            return False
    
    def insertar_evento(self, ubicacion, tipo_evento, descripcion, sensor):
        """Inserta un evento en la base de datos."""
        if not self.conn:
            print("❌ Error: No hay conexión a la base de datos")
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
            
            print(f"🚆 Evento Shinkansen registrado: ({evento_id}) {tipo_evento} - {descripcion}")
            return True
            
        except Exception as e:
            print(f"❌ Error al insertar evento Shinkansen: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def procesar_llegada_tren(self):
        """Procesa la llegada del tren Shinkansen a la estación."""
        tiempo_actual = time.time()
        
        if tiempo_actual - self.ultima_llegada_tren >= self.config['intervalo_tren_llegada']:
            # Registrar llegada del tren
            descripcion = "Tren Shinkansen llegando a la estacion. Abriendo puertas automaticamente."
            self.insertar_evento("Estacion Shinkansen", "Tren Llegada", descripcion, "PIR/Sistema")
            
            self.ultima_llegada_tren = tiempo_actual
            self.tren_en_estacion = True
            
            print("🚆 ¡TREN SHINKANSEN DETECTADO EN LA ESTACIÓN!")
            print("🚪 Activando apertura automática de puertas...")
            
            return True
        return False
    
    def procesar_estado_puerta(self, estado):
        """Procesa cambios en el estado de la puerta."""
        tiempo_actual = time.time()
        
        if tiempo_actual - self.ultima_puerta_evento >= self.config['intervalo_puerta']:
            if estado == "abierta" and not self.puerta_abierta:
                descripcion = "Puerta de la estacion abierta. Pasajeros pueden abordar/descender."
                self.insertar_evento("Estacion Shinkansen", "Puerta Abierta", descripcion, "Motor4")
                self.puerta_abierta = True
                self.ultima_puerta_evento = tiempo_actual
                print("🚪 PUERTA ABIERTA - Pasajeros pueden abordar")
                
            elif estado == "cerrada" and self.puerta_abierta:
                descripcion = "Puerta de la estacion cerrada. Preparando partida del tren."
                self.insertar_evento("Estacion Shinkansen", "Puerta Cerrada", descripcion, "Motor4")
                self.puerta_abierta = False
                self.tren_en_estacion = False  # Tren se va cuando se cierra la puerta
                self.ultima_puerta_evento = tiempo_actual
                print("🚪 PUERTA CERRADA - Tren preparado para partir")
    
    def procesar_ascensores(self, datos_json):
        """Procesa datos de los ascensores para detectar actividad."""
        try:
            ascensores_activos_ahora = 0
            
            for ascensor in datos_json.get('ascensores', []):
                if ascensor.get('activo', False):
                    ascensores_activos_ahora += 1
            
            # Si hay más ascensores activos que antes, podría indicar llegada de pasajeros
            if (ascensores_activos_ahora > self.ascensores_activos and 
                self.config['detectar_por_ascensores']):
                
                tiempo_actual = time.time()
                if tiempo_actual - self.ultimo_ascensor_evento >= self.config['intervalo_ascensor']:
                    descripcion = f"Actividad en ascensores detectada ({ascensores_activos_ahora} activos). Posible llegada de pasajeros."
                    self.insertar_evento("Estacion Shinkansen", "Actividad Ascensores", descripcion, "Motores1-3")
                    self.ultimo_ascensor_evento = tiempo_actual
                    print(f"🏢 ACTIVIDAD EN ASCENSORES: {ascensores_activos_ahora} ascensores activos")
            
            self.ascensores_activos = ascensores_activos_ahora
            
        except Exception as e:
            print(f"❌ Error al procesar datos de ascensores: {e}")
    
    def procesar_datos_json(self, linea):
        """Procesa datos JSON del Arduino."""
        try:
            # Buscar el JSON entre JSON_START y JSON_END
            if "JSON_START" in linea:
                return "start"
            elif "JSON_END" in linea:
                return "end"
            elif linea.strip().startswith("{") and linea.strip().endswith("}"):
                # Es una línea JSON
                datos = json.loads(linea.strip())
                
                # Procesar estado de la puerta
                puerta_estado = datos.get('puerta', {}).get('estado', '')
                if puerta_estado:
                    self.procesar_estado_puerta(puerta_estado)
                
                # Procesar datos de ascensores
                self.procesar_ascensores(datos)
                
                # Si la puerta se abre Y hay PIR activo, es llegada de tren
                pir_activo = datos.get('puerta', {}).get('sensor_pir', False)
                if (pir_activo and self.config['detectar_por_movimiento_pir'] and 
                    not self.tren_en_estacion):
                    self.procesar_llegada_tren()
                
                return "processed"
        except json.JSONDecodeError:
            return None
        except Exception as e:
            print(f"❌ Error al procesar JSON: {e}")
            return None
    
    def iniciar_monitoreo(self):
        """Inicia el monitoreo del Arduino Shinkansen."""
        # Verificar conexiones
        if not self.conn and not self.conectar_bd():
            print("❌ No se pudo conectar a la base de datos. Abortando.")
            return False
        
        if not self.ser and not self.conectar_arduino():
            print("❌ No se pudo conectar al Arduino Shinkansen. Abortando.")
            return False
        
        # Registrar inicio del sistema
        self.insertar_evento("Estacion Tokyo", "Sistema", "Sistema de monitoreo Shinkansen iniciado", "Arduino-Motores")
        
        try:
            print("=== 🚆 MONITOREO SHINKANSEN INICIADO ===")
            print("Detectando:")
            if self.config['detectar_por_movimiento_pir']:
                print("  ✅ Llegada de tren por sensor PIR")
            if self.config['detectar_por_ascensores']:
                print("  ✅ Actividad de ascensores")
            print("  ✅ Estados de puerta (abierta/cerrada)")
            print("Presiona Ctrl+C para detener")
            print("-" * 50)
            
            json_buffer = ""
            capturando_json = False
            
            while True:
                if self.ser.in_waiting > 0:
                    try:
                        # Leer línea del Arduino
                        linea = self.ser.readline().decode('latin1', errors='replace').strip()
                        if not linea:
                            continue
                        
                        # Procesar datos JSON
                        resultado_json = self.procesar_datos_json(linea)
                        
                        if resultado_json == "start":
                            capturando_json = True
                            json_buffer = ""
                            continue
                        elif resultado_json == "end":
                            capturando_json = False
                            continue
                        elif resultado_json == "processed":
                            continue
                        
                        # Si estamos capturando JSON, agregar al buffer
                        if capturando_json:
                            json_buffer += linea
                            continue
                        
                        # Mostrar mensaje recibido (solo si no es JSON)
                        if not (linea.startswith("{") or "JSON" in linea):
                            print(f"📟 Arduino: {linea}")
                        
                        # ===== DETECTAR MENSAJES ESPECÍFICOS =====
                        
                        # Detectar movimiento PIR (llegada de tren)
                        if "MOVIMIENTO DETECTADO" in linea and self.config['detectar_por_movimiento_pir']:
                            if not self.tren_en_estacion:
                                self.procesar_llegada_tren()
                        
                        # Detectar apertura de puerta
                        elif "Puerta ABIERTA" in linea or "PUERTA ABIERTA" in linea:
                            self.procesar_estado_puerta("abierta")
                        
                        # Detectar cierre de puerta
                        elif "Puerta CERRADA" in linea or "PUERTA CERRADA" in linea:
                            self.procesar_estado_puerta("cerrada")
                        
                        # Detectar actividad de ascensores
                        elif "Ascensores activados" in linea and self.config['detectar_por_ascensores']:
                            tiempo_actual = time.time()
                            if tiempo_actual - self.ultimo_ascensor_evento >= self.config['intervalo_ascensor']:
                                descripcion = "Ascensores en funcionamiento. Pasajeros subiendo/bajando."
                                self.insertar_evento("Estacion Tokyo", "Actividad Ascensores", descripcion, "Motores1-3")
                                self.ultimo_ascensor_evento = tiempo_actual
                                print("🏢 ASCENSORES ACTIVOS")
                        
                        # Detectar mensajes de llegada directos
                        elif any(palabra in linea.lower() for palabra in ["tren", "shinkansen", "llegada", "estacion"]):
                            if not self.tren_en_estacion:
                                self.procesar_llegada_tren()
                                
                    except Exception as e:
                        print(f"❌ Error al procesar línea: {e}")
                
                time.sleep(0.1)  # Pequeña pausa para no saturar CPU
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoreo Shinkansen detenido por el usuario")
        except Exception as e:
            print(f"❌ Error en el monitoreo Shinkansen: {e}")
        finally:
            # Cerrar conexiones
            if self.ser:
                self.ser.close()
                print("🔌 Conexión serial cerrada")
            
            if self.conn:
                # Registrar cierre del sistema
                self.insertar_evento("Estacion Tokyo", "Sistema", "Sistema de monitoreo Shinkansen detenido", "Arduino-Motores")
                self.conn.close()
                print("💾 Conexión a base de datos cerrada")
            
            print("🚆 Monitoreo Shinkansen finalizado")
    
    def obtener_registros(self):
        """Devuelve los registros locales de eventos para depuración."""
        return self.registros
    
    def obtener_estado_actual(self):
        """Devuelve el estado actual del sistema."""
        return {
            'tren_en_estacion': self.tren_en_estacion,
            'puerta_abierta': self.puerta_abierta,
            'ascensores_activos': self.ascensores_activos,
            'ultima_llegada': self.ultima_llegada_tren,
            'registros_totales': len(self.registros)
        }

# Función principal para ejecutar el monitor Shinkansen
def main():
    print("=== 🚆 Monitor Shinkansen - Estación Tokyo ===")
    print(f"Este programa captura datos del puerto {CONFIG_SHINKANSEN['puerto_com']} (Arduino de Motores)")
    print("Detecta llegadas de tren, estados de puerta y actividad de ascensores.")
    print("Los datos se registran en la tabla 'eventos' de la base de datos.")
    print()
    
    monitor = MonitorShinkansen()
    monitor.iniciar_monitoreo()

if __name__ == "__main__":
    main()