import psycopg2
import psycopg2.extensions
from datetime import datetime

class ConexionDB:
    def __init__(self):
        self.host = 'proyecto-universidad-instance-1.cla848gew495.us-east-2.rds.amazonaws.com'
        self.port = '5432'
        self.dbname = 'arduino_monitoreo'
        self.user = 'postgres'
        self.password = 'Matematicas123890'
        
        # Configurar codificación por defecto para psycopg2
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

    def _conectar(self):
        """Método interno para establecer conexión a la base de datos."""
        try:
            # Configurar explícitamente el cliente para usar 'latin1' para mejor compatibilidad
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                client_encoding='latin1'
            )
            return conn
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            return None

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

    def _ejecutar_consulta(self, query, params=None):
        """Método interno para ejecutar consultas con manejo de codificación."""
        conn = self._conectar()
        if not conn:
            return None, None
        
        try:
            # Sanitizar parámetros para evitar problemas de codificación
            if params and isinstance(params, (list, tuple)):
                params_limpios = []
                for param in params:
                    if isinstance(param, str):
                        # Sanitizar el texto para evitar problemas de codificación
                        param = self._sanitizar_texto(param)
                    params_limpios.append(param)
                params = params_limpios
            
            cur = conn.cursor()
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            return cur, conn
        except Exception as e:
            print(f"Error al ejecutar consulta: {e}")
            if conn:
                conn.close()
            return None, None

    def verificar_conexion(self):
        """Verifica si la conexión a la base de datos funciona."""
        conn = self._conectar()
        if conn:
            conn.close()
            return True
        return False

    def obtener_eventos(self):
        """Obtiene los últimos 50 eventos registrados en la base de datos."""
        try:
            cur, conn = self._ejecutar_consulta("""
                SELECT fecha_hora, ubicacion, tipo_evento, descripcion 
                FROM eventos 
                ORDER BY fecha_hora DESC 
                LIMIT 50
            """)
            
            if not cur or not conn:
                return []
            
            eventos_raw = cur.fetchall()
            eventos = []
            
            # Sanitizar los resultados
            for evento in eventos_raw:
                fecha_hora, ubicacion, tipo_evento, descripcion = evento
                
                ubicacion = self._sanitizar_texto(ubicacion)
                tipo_evento = self._sanitizar_texto(tipo_evento)
                descripcion = self._sanitizar_texto(descripcion)
                
                eventos.append((fecha_hora, ubicacion, tipo_evento, descripcion))
            
            cur.close()
            conn.close()
            return eventos
        except Exception as e:
            print(f"Error al consultar eventos: {e}")
            return []

    def obtener_eventos_filtrados(self, anio=None, mes=None, dia=None):
        """Obtiene los eventos filtrados por fecha."""
        try:
            query = """
                SELECT fecha_hora, ubicacion, tipo_evento, descripcion 
                FROM eventos 
                WHERE 1=1
            """
            params = []

            if anio:
                query += " AND EXTRACT(YEAR FROM fecha_hora) = %s"
                params.append(anio)
            if mes:
                query += " AND EXTRACT(MONTH FROM fecha_hora) = %s"
                params.append(mes)
            if dia:
                query += " AND EXTRACT(DAY FROM fecha_hora) = %s"
                params.append(dia)

            query += " ORDER BY fecha_hora DESC"
            
            cur, conn = self._ejecutar_consulta(query, params)
            
            if not cur or not conn:
                return []
            
            eventos_raw = cur.fetchall()
            eventos = []
            
            # Sanitizar los resultados
            for evento in eventos_raw:
                fecha_hora, ubicacion, tipo_evento, descripcion = evento
                
                ubicacion = self._sanitizar_texto(ubicacion)
                tipo_evento = self._sanitizar_texto(tipo_evento)
                descripcion = self._sanitizar_texto(descripcion)
                
                eventos.append((fecha_hora, ubicacion, tipo_evento, descripcion))
            
            cur.close()
            conn.close()
            return eventos
        except Exception as e:
            print(f"Error al consultar eventos filtrados: {e}")
            return []

    def obtener_ultimo_evento(self):
        """Obtiene el último evento crítico (Alerta Sísmica o Incendio)."""
        try:
            cur, conn = self._ejecutar_consulta("""
                SELECT fecha_hora, ubicacion, tipo_evento, descripcion
                FROM eventos
                WHERE tipo_evento IN ('Alerta Sismica', 'Incendio')
                ORDER BY fecha_hora DESC
                LIMIT 1
            """)
            
            if not cur or not conn:
                return None
            
            ultimo_evento = cur.fetchone()
            
            # Sanitizar resultado si existe
            if ultimo_evento:
                fecha_hora, ubicacion, tipo_evento, descripcion = ultimo_evento
                
                ubicacion = self._sanitizar_texto(ubicacion)
                tipo_evento = self._sanitizar_texto(tipo_evento)
                descripcion = self._sanitizar_texto(descripcion)
                
                ultimo_evento = (fecha_hora, ubicacion, tipo_evento, descripcion)
            
            cur.close()
            conn.close()
            return ultimo_evento
        except Exception as e:
            print(f"Error al consultar último evento: {e}")
            return None

    def obtener_ultimo_evento_por_tipo(self, tipo_evento):
        """Obtiene el último evento de un tipo específico."""
        try:
            # Sanitizar el tipo_evento
            if isinstance(tipo_evento, str):
                tipo_evento = self._sanitizar_texto(tipo_evento)
            
            cur, conn = self._ejecutar_consulta("""
                SELECT fecha_hora, ubicacion, tipo_evento, descripcion
                FROM eventos
                WHERE tipo_evento = %s
                ORDER BY fecha_hora DESC
                LIMIT 1
            """, (tipo_evento,))
            
            if not cur or not conn:
                return None
            
            resultado = cur.fetchone()
            
            # Sanitizar resultado si existe
            if resultado:
                fecha_hora, ubicacion, tipo_evento, descripcion = resultado
                
                ubicacion = self._sanitizar_texto(ubicacion)
                tipo_evento = self._sanitizar_texto(tipo_evento)
                descripcion = self._sanitizar_texto(descripcion)
                
                resultado = (fecha_hora, ubicacion, tipo_evento, descripcion)
            
            cur.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error al consultar último evento por tipo: {e}")
            return None

    def obtener_eventos_por_tipo(self, tipo_evento):
        """Obtiene todos los eventos de un tipo específico."""
        try:
            # Sanitizar el tipo_evento
            if isinstance(tipo_evento, str):
                tipo_evento = self._sanitizar_texto(tipo_evento)
            
            cur, conn = self._ejecutar_consulta("""
                SELECT fecha_hora, ubicacion, tipo_evento, descripcion
                FROM eventos
                WHERE tipo_evento = %s
                ORDER BY fecha_hora DESC
            """, (tipo_evento,))
            
            if not cur or not conn:
                return []
            
            eventos_raw = cur.fetchall()
            eventos = []
            
            # Sanitizar los resultados
            for evento in eventos_raw:
                fecha_hora, ubicacion, tipo_evento, descripcion = evento
                
                ubicacion = self._sanitizar_texto(ubicacion)
                tipo_evento = self._sanitizar_texto(tipo_evento)
                descripcion = self._sanitizar_texto(descripcion)
                
                eventos.append((fecha_hora, ubicacion, tipo_evento, descripcion))
            
            cur.close()
            conn.close()
            return eventos
        except Exception as e:
            print(f"Error al consultar eventos por tipo: {e}")
            return []

    def obtener_estadisticas_eventos(self):
        """Obtiene estadísticas sobre los tipos de eventos."""
        try:
            cur, conn = self._ejecutar_consulta("""
                SELECT 
                    tipo_evento, 
                    COUNT(*) as total, 
                    MAX(fecha_hora) as ultimo_registro
                FROM eventos
                GROUP BY tipo_evento
                ORDER BY total DESC
            """)
            
            if not cur or not conn:
                return []
            
            estadisticas_raw = cur.fetchall()
            estadisticas = []
            
            # Sanitizar los resultados
            for stat in estadisticas_raw:
                tipo_evento, total, ultimo_registro = stat
                
                tipo_evento = self._sanitizar_texto(tipo_evento)
                
                estadisticas.append((tipo_evento, total, ultimo_registro))
            
            cur.close()
            conn.close()
            return estadisticas
        except Exception as e:
            print(f"Error al consultar estadísticas: {e}")
            return []

    def insertar_evento_manual(self, ubicacion, tipo_evento, descripcion, sensor):
        """Permite insertar eventos manualmente desde la aplicación."""
        try:
            # Sanitizar los datos
            if isinstance(ubicacion, str):
                ubicacion = self._sanitizar_texto(ubicacion)
            if isinstance(tipo_evento, str):
                tipo_evento = self._sanitizar_texto(tipo_evento)
            if isinstance(descripcion, str):
                descripcion = self._sanitizar_texto(descripcion)
            if isinstance(sensor, str):
                sensor = self._sanitizar_texto(sensor)
            
            cur, conn = self._ejecutar_consulta("""
                INSERT INTO eventos 
                    (ubicacion, tipo_evento, descripcion, sensor) 
                VALUES 
                    (%s, %s, %s, %s)
                RETURNING id
            """, (ubicacion, tipo_evento, descripcion, sensor))
            
            if not cur or not conn:
                return False
            
            evento_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"Evento insertado manualmente: ID {evento_id}, {tipo_evento}")
            return True
        except Exception as e:
            print(f"Error al insertar evento manual: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
            
    def obtener_ultimo_id(self):
        """Obtiene el ID del último evento insertado en la base de datos."""
        try:
            cur, conn = self._ejecutar_consulta("""
                SELECT id FROM eventos 
                ORDER BY fecha_hora DESC 
                LIMIT 1
            """)
            
            if not cur or not conn:
                return None
            
            resultado = cur.fetchone()
            ultimo_id = resultado[0] if resultado else None
            
            cur.close()
            conn.close()
            return ultimo_id
        except Exception as e:
            print(f"Error al obtener último ID: {e}")
            return None
            
    def obtener_evento_por_id(self, evento_id):
        """Obtiene un evento específico por su ID."""
        try:
            cur, conn = self._ejecutar_consulta("""
                SELECT fecha_hora, ubicacion, tipo_evento, descripcion
                FROM eventos
                WHERE id = %s
            """, (evento_id,))
            
            if not cur or not conn:
                return None
            
            resultado = cur.fetchone()
            
            # Sanitizar resultado si existe
            if resultado:
                fecha_hora, ubicacion, tipo_evento, descripcion = resultado
                
                ubicacion = self._sanitizar_texto(ubicacion)
                tipo_evento = self._sanitizar_texto(tipo_evento)
                descripcion = self._sanitizar_texto(descripcion)
                
                resultado = (fecha_hora, ubicacion, tipo_evento, descripcion)
            
            cur.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error al consultar evento por ID: {e}")
            return None