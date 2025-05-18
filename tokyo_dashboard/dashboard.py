from flask import Flask, render_template, jsonify, request, send_from_directory
from conexion import ConexionDB
import re
import datetime
import logging
import os
import json
import time

# Configurar logging para registrar errores y eventos importantes
logging.basicConfig(
    filename='dashboard_web.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_para_dashboard'

# Variables globales para rastrear estados
ultimo_id_alertado = None
temperatura_actual = "--"
alerta_actual = "Sin eventos recientes"

# Inicializar conexión a la base de datos
db = None
try:
    db = ConexionDB()
    if db.verificar_conexion():
        logging.info("Conexión a la base de datos establecida correctamente")
    else:
        logging.error("Falló la conexión inicial a la base de datos")
except Exception as e:
    logging.error(f"Error al inicializar conexión a la base de datos: {e}")

# Función para reconectar a la base de datos
def reconectar_bd():
    """Intenta reconectar a la base de datos."""
    global db
    intentos = 0
    max_intentos = 3
    
    while intentos < max_intentos:
        try:
            db = ConexionDB()
            if db.verificar_conexion():
                logging.info("Reconexión a la base de datos exitosa")
                return True
            time.sleep(2)  # Esperar antes de reintentar
        except Exception as e:
            mensaje_error = f"Error al reconectar: {e}"
            logging.error(mensaje_error)
            print(mensaje_error)
        
        intentos += 1
    
    logging.error("Fallaron todos los intentos de reconexión")
    return False

@app.route('/')
def index():
    """Página principal del dashboard."""
    global db
    
    # Verificar conexión a la base de datos
    if not db or not db.verificar_conexion():
        if not reconectar_bd():
            return render_template('error.html', 
                                  mensaje="No se pudo conectar a la base de datos. Verifique la configuración en conexion.py")
    
    return render_template('index.html')

@app.route('/obtener_eventos')
def obtener_eventos():
    """API para obtener los eventos más recientes."""
    global db
    
    try:
        # Verificar conexión a la base de datos
        if not db or not db.verificar_conexion():
            if not reconectar_bd():
                return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        eventos = db.obtener_eventos()
        
        # Si no hay eventos
        if not eventos:
            return jsonify([])
        
        # Formatear los datos para JSON
        eventos_formateados = []
        for ev in eventos:
            fecha = ev[0]
            if isinstance(fecha, datetime.datetime):
                fecha = fecha.strftime("%Y-%m-%d %H:%M:%S")
                
            eventos_formateados.append({
                'fecha': fecha,
                'ubicacion': ev[1],
                'tipo': ev[2],
                'descripcion': ev[3]
            })
            
        return jsonify(eventos_formateados)
    except Exception as e:
        logging.error(f"Error al obtener eventos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/eventos_filtrados')
def eventos_filtrados():
    """API para obtener eventos filtrados por fecha."""
    global db
    
    try:
        # Obtener parámetros de la solicitud
        anio = request.args.get('anio', default=None, type=int)
        mes = request.args.get('mes', default=None, type=int)
        dia = request.args.get('dia', default=None, type=int)
        
        # Validar parámetros
        if mes and (mes < 1 or mes > 12):
            return jsonify({'error': 'El mes debe estar entre 1 y 12'}), 400
        if dia and (dia < 1 or dia > 31):
            return jsonify({'error': 'El día debe estar entre 1 y 31'}), 400
        
        # Verificar conexión a la base de datos
        if not db or not db.verificar_conexion():
            if not reconectar_bd():
                return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        eventos = db.obtener_eventos_filtrados(anio, mes, dia)
        
        # Si no hay eventos
        if not eventos:
            return jsonify([])
        
        # Formatear los datos para JSON
        eventos_formateados = []
        for ev in eventos:
            fecha = ev[0]
            if isinstance(fecha, datetime.datetime):
                fecha = fecha.strftime("%Y-%m-%d %H:%M:%S")
                
            eventos_formateados.append({
                'fecha': fecha,
                'ubicacion': ev[1],
                'tipo': ev[2],
                'descripcion': ev[3]
            })
            
        return jsonify(eventos_formateados)
    except Exception as e:
        logging.error(f"Error al obtener eventos filtrados: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/eventos_por_tipo/<tipo>')
def eventos_por_tipo(tipo):
    """API para obtener eventos filtrados por tipo."""
    global db
    
    try:
        # Si es "Todos", redirigir a todos los eventos
        if tipo == "Todos":
            return obtener_eventos()
        
        # Verificar conexión a la base de datos
        if not db or not db.verificar_conexion():
            if not reconectar_bd():
                return jsonify({'error': 'Error de conexión a la base de datos'}), 500
            
        eventos = db.obtener_eventos_por_tipo(tipo)
        
        # Si no hay eventos
        if not eventos:
            return jsonify([])
        
        # Formatear los datos para JSON
        eventos_formateados = []
        for ev in eventos:
            fecha = ev[0]
            if isinstance(fecha, datetime.datetime):
                fecha = fecha.strftime("%Y-%m-%d %H:%M:%S")
                
            eventos_formateados.append({
                'fecha': fecha,
                'ubicacion': ev[1],
                'tipo': ev[2],
                'descripcion': ev[3]
            })
            
        return jsonify(eventos_formateados)
    except Exception as e:
        logging.error(f"Error al obtener eventos por tipo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/temperatura_actual')
def obtener_temperatura_actual():
    """API para obtener la temperatura actual."""
    global db, temperatura_actual
    
    try:
        # Verificar conexión a la base de datos
        if not db or not db.verificar_conexion():
            if not reconectar_bd():
                return jsonify({'error': 'Error de conexión a la base de datos', 'temperatura': '--'}), 500
            
        ultimo_temp = db.obtener_ultimo_evento_por_tipo("Temperatura")
        
        if ultimo_temp:
            _, _, _, descripcion = ultimo_temp
            match = re.search(r'([0-9]+(?:\.[0-9]+)?)', descripcion)
            if match:
                temperatura_actual = match.group(1)
                return jsonify({'temperatura': temperatura_actual})
                
        return jsonify({'temperatura': '--'})
    except Exception as e:
        logging.error(f"Error al obtener temperatura actual: {e}")
        return jsonify({'error': str(e), 'temperatura': '--'}), 500

@app.route('/alertas')
def verificar_alertas():
    """API para verificar si hay nuevas alertas."""
    global db, ultimo_id_alertado, alerta_actual
    
    try:
        # Verificar conexión a la base de datos
        if not db or not db.verificar_conexion():
            if not reconectar_bd():
                return jsonify({
                    'hay_alerta': False,
                    'mensaje': 'Error de conexión a la base de datos',
                    'tipo': None,
                    'error': True
                }), 500
            
        # Obtener el ID del último evento
        try:
            nuevo_id = db.obtener_ultimo_id()
        except Exception as e:
            logging.error(f"Error al obtener último ID: {e}")
            return jsonify({
                'hay_alerta': False,
                'mensaje': f'Error al obtener último ID: {e}',
                'tipo': None,
                'error': True
            }), 500
        
        if not nuevo_id:
            alerta_actual = "Sin eventos recientes"
            return jsonify({
                'hay_alerta': False,
                'mensaje': 'Sin eventos recientes',
                'tipo': None
            })
            
        # Verificar si es un evento nuevo
        if nuevo_id != ultimo_id_alertado:
            # Actualizar el ID almacenado
            id_anterior = ultimo_id_alertado
            ultimo_id_alertado = nuevo_id
            
            # Obtener detalles del evento
            try:
                ultimo_evento = db.obtener_evento_por_id(nuevo_id)
            except Exception as e:
                logging.error(f"Error al obtener evento por ID: {e}")
                return jsonify({
                    'hay_alerta': False,
                    'mensaje': f'Error al obtener evento por ID: {e}',
                    'tipo': None,
                    'error': True
                }), 500
            
            if not ultimo_evento:
                alerta_actual = "Sin eventos recientes"
                return jsonify({
                    'hay_alerta': False,
                    'mensaje': 'Sin eventos recientes',
                    'tipo': None
                })
                
            fecha_hora, ubicacion, tipo_evento, descripcion = ultimo_evento
            
            # Si es un evento crítico
            if tipo_evento in ['Alerta Sismica', 'Incendio']:
                # Formatear fecha
                fecha_formateada = fecha_hora
                if isinstance(fecha_hora, datetime.datetime):
                    fecha_formateada = fecha_hora.strftime("%H:%M:%S")
                
                # Actualizar mensaje de alerta
                alerta_actual = f"{tipo_evento} - {descripcion} ({fecha_formateada})"
                
                # Solo mostrar alerta si no es el primer evento al iniciar
                if id_anterior is not None:
                    return jsonify({
                        'hay_alerta': True,
                        'mensaje': alerta_actual,
                        'tipo': tipo_evento,
                        'descripcion': descripcion,
                        'fecha': str(fecha_formateada)
                    })
            # Si es un evento de temperatura, resetear la alerta a normal
            elif tipo_evento == 'Temperatura':
                # Resetear la alerta a normal - Aquí está el cambio
                alerta_actual = "Sistema operando normalmente"
                return jsonify({
                    'hay_alerta': False,
                    'mensaje': alerta_actual,
                    'tipo': None
                })
            # Si es otro tipo de evento no crítico
            else:
                # No es un evento crítico, mostrar estado normal
                alerta_actual = "Sistema operando normalmente"
        
        # Si no hay nuevas alertas o no son críticas
        return jsonify({
            'hay_alerta': False,
            'mensaje': alerta_actual,
            'tipo': None
        })
    except Exception as e:
        logging.error(f"Error al verificar alertas: {e}")
        return jsonify({
            'hay_alerta': False,
            'mensaje': f'Error al verificar alertas: {e}',
            'tipo': None,
            'error': True
        }), 500

@app.route('/estado_dashboard')
def estado_dashboard():
    """API para obtener el estado general del dashboard."""
    global db
    
    try:
        # Verificar conexión a la base de datos
        if not db or not db.verificar_conexion():
            if not reconectar_bd():
                return jsonify({
                    'estado': 'error',
                    'mensaje': 'Error de conexión a la base de datos'
                }), 500
            
        # Obtener temperatura
        temp_response = obtener_temperatura_actual()
        temp_data = json.loads(temp_response.get_data(as_text=True))
        
        # Obtener alertas
        alerta_response = verificar_alertas()
        alerta_data = json.loads(alerta_response.get_data(as_text=True))
        
        # Componer respuesta
        return jsonify({
            'estado': 'ok',
            'temperatura': temp_data.get('temperatura', '--'),
            'alerta': alerta_data
        })
    except Exception as e:
        logging.error(f"Error al obtener estado del dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/sound/<filename>')
def serve_sound(filename):
    """Sirve archivos de sonido."""
    return send_from_directory(os.path.join(app.root_path, 'static', 'sound'), filename)

@app.errorhandler(404)
def page_not_found(e):
    """Maneja errores 404."""
    return render_template('error.html', mensaje="Página no encontrada"), 404

@app.errorhandler(500)
def server_error(e):
    """Maneja errores 500."""
    return render_template('error.html', mensaje="Error interno del servidor"), 500

# Crear las carpetas necesarias al iniciar la aplicación
def crear_estructura_carpetas():
    """Crea la estructura de carpetas necesaria para la aplicación."""
    carpetas = [
        'static',
        'static/css',
        'static/js',
        'static/sound',
        'templates'
    ]
    
    for carpeta in carpetas:
        ruta_completa = os.path.join(os.path.dirname(os.path.abspath(__file__)), carpeta)
        if not os.path.exists(ruta_completa):
            os.makedirs(ruta_completa)
            logging.info(f"Carpeta creada: {ruta_completa}")

if __name__ == '__main__':
    # Crear estructura de carpetas
    crear_estructura_carpetas()
    
    # Copiar archivo de sonido si existe
    ruta_origen = r"C:\Users\braya\Desktop\proyecto arquitectura dashboard\proyecto arquitectura\recursos\sonido\random-alarm-319318.mp3"
    if os.path.exists(ruta_origen):
        ruta_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'sound', 'alerta.mp3')
        try:
            import shutil
            shutil.copy2(ruta_origen, ruta_destino)
            logging.info(f"Archivo de sonido copiado a: {ruta_destino}")
        except Exception as e:
            logging.error(f"Error al copiar archivo de sonido: {e}")
    
    # Iniciar el servidor web
    app.run(debug=True, host='0.0.0.0', port=5000)