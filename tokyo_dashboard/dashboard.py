from flask import Flask, render_template, jsonify, request, send_from_directory
from conexion import ConexionDB
import re
import datetime
import logging
import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

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

# Lista de correos electrónicos para alertas críticas
CORREOS_ALERTAS = [
    "mgilr@miumg.edu.gt",
    "bmirandav1@miumg.edu.gt", 
    "fguerrat@miumg.edu.gt",
    "bgomezq1@miumg.edu.gt",
    "msantosl5@miumg.edu.gt",
    "mjimenezp8@miumg.edu.gt"
]

class AlertEmailSender:
    def __init__(self):
        self.email = "umg2876@gmail.com"
        self.password = "ajxo dwel eqpd rzag"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sistema_nombre = "Sistema de Monitoreo Inteligente"
        self.empresa = "UMG - Ingeniería en Sistemas"

    def _crear_mensaje_html(self, tipo_alerta, descripcion, fecha_hora, ubicacion, severidad="CRÍTICA"):
        """Crea un mensaje HTML profesional para las alertas."""
        
        # Colores según el tipo de alerta
        colores = {
            "Alerta Sismica": {"bg": "#FF6B6B", "icon": "🌍", "color": "#FFFFFF"},
            "Incendio": {"bg": "#FF4757", "icon": "🔥", "color": "#FFFFFF"},
            "Temperatura": {"bg": "#FFA502", "icon": "🌡️", "color": "#FFFFFF"},
            "Normal": {"bg": "#2ED573", "icon": "✅", "color": "#FFFFFF"}
        }
        
        config_color = colores.get(tipo_alerta, colores["Normal"])
        fecha_formateada = fecha_hora.strftime("%d/%m/%Y a las %H:%M:%S") if isinstance(fecha_hora, datetime.datetime) else str(fecha_hora)
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Alerta del Sistema</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f7fa;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, {config_color['bg']}, #1e3c72); color: white; padding: 30px; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 10px;">{config_color['icon']}</div>
                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">ALERTA {severidad}</h1>
                    <p style="margin: 5px 0 0 0; font-size: 16px; opacity: 0.9;">{self.sistema_nombre}</p>
                </div>
                
                <!-- Contenido Principal -->
                <div style="padding: 40px 30px;">
                    
                    <!-- Información de la Alerta -->
                    <div style="background-color: #f8f9fa; border-left: 4px solid {config_color['bg']}; padding: 20px; margin-bottom: 30px; border-radius: 4px;">
                        <h2 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 20px;">Detalles del Evento</h2>
                        
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #34495e;">📋 Tipo de Alerta:</strong>
                            <span style="background-color: {config_color['bg']}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; margin-left: 10px;">{tipo_alerta}</span>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #34495e;">📝 Descripción:</strong>
                            <p style="margin: 5px 0 0 0; color: #2c3e50; background-color: white; padding: 10px; border-radius: 4px; border: 1px solid #e9ecef;">{descripcion}</p>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <strong style="color: #34495e;">📍 Ubicación:</strong>
                            <span style="color: #2c3e50; margin-left: 10px;">{ubicacion}</span>
                        </div>
                        
                        <div style="margin-bottom: 0;">
                            <strong style="color: #34495e;">🕒 Fecha y Hora:</strong>
                            <span style="color: #2c3e50; margin-left: 10px;">{fecha_formateada}</span>
                        </div>
                    </div>
                    
                    <!-- Acciones Recomendadas -->
                    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin-bottom: 30px;">
                        <h3 style="color: #856404; margin: 0 0 15px 0; font-size: 18px;">⚠️ Acciones Recomendadas</h3>
                        <ul style="color: #856404; margin: 0; padding-left: 20px;">
                            <li style="margin-bottom: 8px;">Verificar el estado del sistema inmediatamente</li>
                            <li style="margin-bottom: 8px;">Contactar al personal de emergencia si es necesario</li>
                            <li style="margin-bottom: 8px;">Documentar las acciones tomadas</li>
                            <li style="margin-bottom: 0;">Monitorear la situación hasta su resolución</li>
                        </ul>
                    </div>
                    
                    <!-- Información del Sistema -->
                    <div style="background-color: #e3f2fd; border-radius: 8px; padding: 20px; text-align: center;">
                        <h4 style="color: #1565c0; margin: 0 0 10px 0;">📊 Dashboard de Monitoreo</h4>
                        <p style="color: #1976d2; margin: 0; font-size: 14px;">Accede al dashboard para más detalles: <a href="http://localhost:5000" style="color: #1565c0; text-decoration: none; font-weight: 600;">Sistema de Monitoreo</a></p>
                    </div>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #2c3e50; color: #ecf0f1; padding: 25px; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 16px; font-weight: 600;">{self.empresa}</p>
                    <p style="margin: 0; font-size: 12px; opacity: 0.8;">
                        Este es un mensaje automático generado por el {self.sistema_nombre}.<br>
                        No responder a este correo electrónico.
                    </p>
                    <div style="margin-top: 15px; font-size: 11px; opacity: 0.6;">
                        Generado el {datetime.datetime.now().strftime("%d/%m/%Y a las %H:%M:%S")}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template

    def _crear_mensaje_texto(self, tipo_alerta, descripcion, fecha_hora, ubicacion):
        """Crea una versión en texto plano como respaldo."""
        fecha_formateada = fecha_hora.strftime("%d/%m/%Y a las %H:%M:%S") if isinstance(fecha_hora, datetime.datetime) else str(fecha_hora)
        
        return f"""
🚨 ALERTA CRÍTICA DETECTADA 🚨

{self.sistema_nombre}
{self.empresa}

═══════════════════════════════════════════

DETALLES DEL EVENTO:
📋 Tipo: {tipo_alerta}
📝 Descripción: {descripcion}
📍 Ubicación: {ubicacion}
🕒 Fecha/Hora: {fecha_formateada}

═══════════════════════════════════════════

⚠️  ACCIONES INMEDIATAS REQUERIDAS:
• Verificar el estado del sistema
• Contactar personal de emergencia si necesario
• Documentar acciones tomadas
• Monitorear hasta resolución

═══════════════════════════════════════════

📊 Dashboard: http://localhost:5000

---
Mensaje automático - No responder
Generado: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
        """

    def enviar_alerta(self, to_email, tipo_alerta, descripcion, fecha_hora, ubicacion):
        """Envía una alerta individual a un correo específico."""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.sistema_nombre} <{self.email}>"
            msg["To"] = to_email
            msg["Subject"] = f"🚨 {tipo_alerta.upper()} - {self.sistema_nombre}"
            
            # Crear versiones texto y HTML
            texto_plano = self._crear_mensaje_texto(tipo_alerta, descripcion, fecha_hora, ubicacion)
            mensaje_html = self._crear_mensaje_html(tipo_alerta, descripcion, fecha_hora, ubicacion)
            
            # Adjuntar ambas versiones
            parte_texto = MIMEText(texto_plano, "plain", "utf-8")
            parte_html = MIMEText(mensaje_html, "html", "utf-8")
            
            msg.attach(parte_texto)
            msg.attach(parte_html)
            
            # Enviar correo
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.sendmail(self.email, to_email, msg.as_string())
            server.quit()
            
            logging.info(f"✅ Alerta enviada exitosamente a {to_email}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error al enviar alerta a {to_email}: {str(e)}")
            return False

    def enviar_alerta_critica(self, tipo_alerta, descripcion, fecha_hora, ubicacion):
        """Envía alertas críticas a todos los correos configurados."""
        exitosos = 0
        fallidos = 0
        
        logging.info(f"🚨 Enviando alerta crítica: {tipo_alerta}")
        
        for email in CORREOS_ALERTAS:
            if self.enviar_alerta(email, tipo_alerta, descripcion, fecha_hora, ubicacion):
                exitosos += 1
            else:
                fallidos += 1
        
        logging.info(f"📊 Resumen de envío: {exitosos} exitosos, {fallidos} fallidos")
        return exitosos, fallidos

    def enviar_notificacion_estado(self, estado="NORMAL", temperatura=None):
        """Envía notificaciones de estado del sistema."""
        tipo_mensaje = "Estado del Sistema"
        
        if estado == "NORMAL":
            descripcion = f"El sistema está operando normalmente. Temperatura actual: {temperatura}°C"
            icono = "✅"
        else:
            descripcion = f"Se ha detectado un cambio en el estado del sistema: {estado}"
            icono = "⚠️"
        
        mensaje_simple = f"""
{icono} {tipo_mensaje}

{descripcion}

Fecha: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Sistema: {self.sistema_nombre}

---
Notificación automática del dashboard
        """
        
        try:
            exitosos = 0
            for email in CORREOS_ALERTAS:
                msg = MIMEText(mensaje_simple, "plain", "utf-8")
                msg["From"] = f"{self.sistema_nombre} <{self.email}>"
                msg["To"] = email
                msg["Subject"] = f"{icono} {tipo_mensaje} - {datetime.datetime.now().strftime('%H:%M')}"
                
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.email, self.password)
                server.sendmail(self.email, email, msg.as_string())
                server.quit()
                exitosos += 1
            
            logging.info(f"✅ Notificación de estado enviada a {exitosos} destinatarios")
            return exitosos, 0
            
        except Exception as e:
            logging.error(f"❌ Error al enviar notificación de estado: {e}")
            return 0, 1

# Inicializar AlertEmailSender
email_sender = AlertEmailSender()

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
                    # ENVÍO DE CORREO ELECTRÓNICO PARA ALERTAS CRÍTICAS
                    try:
                        exitosos, fallidos = email_sender.enviar_alerta_critica(
                            tipo_evento, 
                            descripcion, 
                            fecha_hora, 
                            ubicacion
                        )
                        logging.info(f"Alerta crítica procesada: {exitosos} correos enviados exitosamente, {fallidos} fallidos")
                    except Exception as e:
                        logging.error(f"Error al enviar alertas por correo: {e}")
                    
                    return jsonify({
                        'hay_alerta': True,
                        'mensaje': alerta_actual,
                        'tipo': tipo_evento,
                        'descripcion': descripcion,
                        'fecha': str(fecha_formateada),
                        'correos_enviados': True  # Indicar que se enviaron correos
                    })
            # Si es un evento de temperatura, resetear la alerta a normal
            elif tipo_evento == 'Temperatura':
                # Resetear la alerta a normal
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

@app.route('/configurar_correos', methods=['GET', 'POST'])
def configurar_correos():
    """API para ver y actualizar la lista de correos de alerta."""
    global CORREOS_ALERTAS
    
    if request.method == 'GET':
        return jsonify({
            'correos': CORREOS_ALERTAS,
            'total': len(CORREOS_ALERTAS)
        })
    
    elif request.method == 'POST':
        try:
            datos = request.get_json()
            nuevos_correos = datos.get('correos', [])
            
            # Validar que sean correos válidos
            import re
            patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            correos_validos = []
            
            for correo in nuevos_correos:
                if re.match(patron_email, correo.strip()):
                    correos_validos.append(correo.strip())
            
            if correos_validos:
                CORREOS_ALERTAS = correos_validos
                logging.info(f"Lista de correos actualizada: {len(correos_validos)} correos")
                return jsonify({
                    'success': True,
                    'mensaje': f'Lista actualizada con {len(correos_validos)} correos válidos',
                    'correos': CORREOS_ALERTAS
                })
            else:
                return jsonify({
                    'success': False,
                    'mensaje': 'No se encontraron correos válidos'
                }), 400
                
        except Exception as e:
            logging.error(f"Error al actualizar correos: {e}")
            return jsonify({
                'success': False,
                'mensaje': f'Error al actualizar: {str(e)}'
            }), 500

@app.route('/test_email')
def test_email():
    """API para probar el envío de correos (solo para desarrollo)."""
    try:
        # Prueba de alerta crítica
        exitosos, fallidos = email_sender.enviar_alerta_critica(
            "Prueba del Sistema",
            "Este es un correo de prueba del sistema de alertas - Todas las funciones operando correctamente",
            datetime.datetime.now(),
            "Dashboard de Prueba - Laboratorio UMG"
        )
        
        # Prueba de notificación de estado
        exitosos_estado, fallidos_estado = email_sender.enviar_notificacion_estado("NORMAL", "23.5")
        
        return jsonify({
            'success': True,
            'mensaje': f'Pruebas completadas - Alertas: {exitosos} exitosos, {fallidos} fallidos | Estado: {exitosos_estado} exitosos',
            'alertas_criticas': {'exitosos': exitosos, 'fallidos': fallidos},
            'notificaciones_estado': {'exitosos': exitosos_estado, 'fallidos': fallidos_estado},
            'total_correos': len(CORREOS_ALERTAS)
        })
    except Exception as e:
        logging.error(f"Error en prueba completa de correos: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error en las pruebas: {str(e)}'
        }), 500

@app.route('/enviar_reporte_estado')
def enviar_reporte_estado():
    """API para enviar un reporte del estado actual del sistema."""
    try:
        # Obtener temperatura actual
        temp_response = obtener_temperatura_actual()
        temp_data = json.loads(temp_response.get_data(as_text=True))
        temperatura = temp_data.get('temperatura', '--')
        
        # Enviar notificación de estado
        exitosos, fallidos = email_sender.enviar_notificacion_estado("NORMAL", temperatura)
        
        return jsonify({
            'success': True,
            'mensaje': f'Reporte de estado enviado: {exitosos} exitosos, {fallidos} fallidos',
            'temperatura_actual': temperatura,
            'correos_enviados': exitosos
        })
    except Exception as e:
        logging.error(f"Error al enviar reporte de estado: {e}")
        return jsonify({
            'success': False,
            'mensaje': f'Error al enviar reporte: {str(e)}'
        }), 500

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
    print("🚀 Dashboard iniciado con sistema de alertas por correo electrónico")
    print(f"📧 Correos configurados para alertas: {len(CORREOS_ALERTAS)}")
    print("🌐 Acceder a: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)