// Variables globales
let dataTable;
let alertaModalElement;
let alertaModal;
let alertaSonido;
let ultimoEvento = null;
let intervaloActualizacion = null;
let errorConexion = false;

// Inicialización cuando el documento está listo
$(document).ready(function() {
    console.log("Inicializando dashboard web...");
    
    // Inicializar la tabla con DataTables
    dataTable = $('#eventos-table').DataTable({
        order: [[0, 'desc']], // Ordenar por fecha descendente
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json'
        },
        pageLength: 10,
        lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "Todos"]],
        responsive: true
    });
    
    // Inicializar componentes
    alertaModalElement = document.getElementById('alertaModal');
    alertaModal = new bootstrap.Modal(alertaModalElement);
    alertaSonido = document.getElementById('alerta-sonido');
    
    // Configurar eventos
    $('#btn-buscar').click(buscarEventos);
    $('#btn-refrescar').click(refrescarDatos);
    $('#tipo-filter').change(filtrarPorTipo);
    
    // Precarga del sonido para mejorar la respuesta
    try {
        alertaSonido.load();
    } catch (e) {
        console.warn("No se pudo precargar el sonido:", e);
    }
    
    // Inicializar datos
    cargarEventos();
    actualizarInfoEstado();
    
    // Configurar actualización automática cada 5 segundos
    intervaloActualizacion = setInterval(actualizarInfoEstado, 5000);
    
    // Detener la actualización automática cuando se cierra la página
    $(window).on('beforeunload', function() {
        if (intervaloActualizacion) {
            clearInterval(intervaloActualizacion);
        }
    });
});

// Función para cargar todos los eventos
function cargarEventos() {
    mostrarCargando(true);
    
    $.ajax({
        url: '/obtener_eventos',
        type: 'GET',
        dataType: 'json',
        success: function(datos) {
            console.log("Eventos recibidos:", datos.length);
            errorConexion = false;
            
            // Limpiar tabla
            dataTable.clear();
            
            // Verificar si hay un error
            if (datos.error) {
                mostrarMensajeEstado("Error: " + datos.error, "danger");
                mostrarCargando(false);
                return;
            }
            
            // Agregar datos a la tabla
            if (datos.length === 0) {
                mostrarMensajeEstado("No se encontraron eventos en la base de datos", "warning");
            } else {
                datos.forEach(function(evento) {
                    const fila = dataTable.row.add([
                        evento.fecha,
                        evento.ubicacion,
                        evento.tipo,
                        evento.descripcion
                    ]).draw(false).node();
                    
                    // Aplicar estilo según el tipo de evento
                    $(fila).addClass(obtenerClaseEvento(evento.tipo));
                });
                
                mostrarMensajeEstado(`Se cargaron ${datos.length} eventos correctamente`, "success");
            }
            
            mostrarCargando(false);
        },
        error: function(xhr, status, error) {
            console.error("Error al cargar eventos:", error);
            errorConexion = true;
            mostrarCargando(false);
            mostrarMensajeEstado("Error de conexión a la base de datos. Reintentando...", "danger");
            
            // Reintentar en 10 segundos
            setTimeout(cargarEventos, 10000);
        }
    });
}

// Función para filtrar eventos por fecha
function buscarEventos() {
    const anio = $('#anio-filter').val();
    const mes = $('#mes-filter').val();
    const dia = $('#dia-filter').val();
    
    // Validar datos
    if (!anio && !mes && !dia) {
        mostrarMensajeEstado("Ingrese al menos un criterio de fecha para filtrar", "warning");
        return;
    }
    
    if ((mes && (mes < 1 || mes > 12)) || (dia && (dia < 1 || dia > 31))) {
        mostrarMensajeEstado("Valores de fecha inválidos", "danger");
        return;
    }
    
    mostrarCargando(true);
    
    $.ajax({
        url: '/eventos_filtrados',
        type: 'GET',
        data: {
            anio: anio || null,
            mes: mes || null,
            dia: dia || null
        },
        dataType: 'json',
        success: function(datos) {
            console.log("Eventos filtrados recibidos:", datos.length);
            errorConexion = false;
            
            // Verificar si hay un error
            if (datos.error) {
                mostrarMensajeEstado("Error: " + datos.error, "danger");
                mostrarCargando(false);
                return;
            }
            
            // Limpiar tabla
            dataTable.clear();
            
            if (datos.length === 0) {
                mostrarMensajeEstado("No se encontraron eventos con los filtros aplicados", "warning");
            } else {
                // Agregar datos a la tabla
                datos.forEach(function(evento) {
                    const fila = dataTable.row.add([
                        evento.fecha,
                        evento.ubicacion,
                        evento.tipo,
                        evento.descripcion
                    ]).draw(false).node();
                    
                    // Aplicar estilo según el tipo de evento
                    $(fila).addClass(obtenerClaseEvento(evento.tipo));
                });
                
                mostrarMensajeEstado(`Se encontraron ${datos.length} eventos con los filtros aplicados`, "success");
            }
            
            mostrarCargando(false);
        },
        error: function(xhr, status, error) {
            console.error("Error al buscar eventos:", error);
            errorConexion = true;
            mostrarCargando(false);
            mostrarMensajeEstado("Error de conexión al buscar eventos. Reintente más tarde.", "danger");
        }
    });
}

// Función para filtrar por tipo de evento
function filtrarPorTipo() {
    const tipoSeleccionado = $('#tipo-filter').val();
    
    mostrarCargando(true);
    
    if (tipoSeleccionado === "Todos") {
        cargarEventos();
        return;
    }
    
    $.ajax({
        url: `/eventos_por_tipo/${encodeURIComponent(tipoSeleccionado)}`,
        type: 'GET',
        dataType: 'json',
        success: function(datos) {
            console.log(`Eventos de tipo ${tipoSeleccionado} recibidos:`, datos.length);
            errorConexion = false;
            
            // Verificar si hay un error
            if (datos.error) {
                mostrarMensajeEstado("Error: " + datos.error, "danger");
                mostrarCargando(false);
                return;
            }
            
            // Limpiar tabla
            dataTable.clear();
            
            if (datos.length === 0) {
                mostrarMensajeEstado(`No se encontraron eventos del tipo '${tipoSeleccionado}'`, "warning");
            } else {
                // Agregar datos a la tabla
                datos.forEach(function(evento) {
                    const fila = dataTable.row.add([
                        evento.fecha,
                        evento.ubicacion,
                        evento.tipo,
                        evento.descripcion
                    ]).draw(false).node();
                    
                    // Aplicar estilo según el tipo de evento
                    $(fila).addClass(obtenerClaseEvento(evento.tipo));
                });
                
                mostrarMensajeEstado(`Se encontraron ${datos.length} eventos del tipo '${tipoSeleccionado}'`, "success");
            }
            
            mostrarCargando(false);
        },
        error: function(xhr, status, error) {
            console.error("Error al filtrar por tipo:", error);
            errorConexion = true;
            mostrarCargando(false);
            mostrarMensajeEstado("Error de conexión al filtrar eventos. Reintente más tarde.", "danger");
        }
    });
}

// Actualizar datos de temperatura y alertas
function actualizarInfoEstado() {
    $.ajax({
        url: '/estado_dashboard',
        type: 'GET',
        dataType: 'json',
        success: function(datos) {
            console.log("Estado actualizado:", datos);
            errorConexion = false;
            
            if (datos.estado === 'ok') {
                // Actualizar temperatura
                actualizarTemperatura(datos.temperatura);
                
                // Verificar alertas
                verificarAlertas(datos.alerta);
            } else {
                console.error("Error en el estado del dashboard:", datos.mensaje);
                mostrarMensajeEstado("Error en el estado del dashboard: " + datos.mensaje, "warning");
            }
        },
        error: function(xhr, status, error) {
            console.error("Error al actualizar estado:", error);
            
            // Si es el primer error, mostrar mensaje
            if (!errorConexion) {
                errorConexion = true;
                mostrarMensajeEstado("Error de conexión con el servidor. Reintentando...", "danger");
            }
        }
    });
}

// Actualizar información de temperatura
function actualizarTemperatura(temperatura) {
    const tempLabel = $('#temperatura-label');
    if (temperatura && temperatura !== '--') {
        tempLabel.html(`<i class="fas fa-thermometer-half me-2"></i> Temperatura actual: ${temperatura} °C`);
        tempLabel.css('color', '#2980b9'); // Azul
    } else {
        tempLabel.html(`<i class="fas fa-thermometer-half me-2"></i> Temperatura actual: -- °C`);
        tempLabel.css('color', '#7f8c8d'); // Gris
    }
}

// Verificar alertas y mostrar notificaciones si hay alguna nueva
function verificarAlertas(alertaData) {
    const alertaLabel = $('#alerta-label');
    
    if (!alertaData) {
        return;
    }
    
    if (alertaData.error) {
        alertaLabel.html(`<i class="fas fa-exclamation-triangle me-2"></i> Error: ${alertaData.error}`);
        alertaLabel.css('color', '#e74c3c'); // Rojo para error
        $('.alerta-panel').removeClass('alerta-activa');
        return;
    }
    
    if (alertaData.hay_alerta) {
        // Actualizar etiqueta de alerta
        alertaLabel.html(`<i class="fas fa-exclamation-triangle me-2"></i> Alerta: ${alertaData.mensaje}`);
        alertaLabel.css('color', '#c0392b'); // Rojo para alertas
        $('.alerta-panel').addClass('alerta-activa');
        
        // Mostrar alerta modal y reproducir sonido si es un evento nuevo
        if (!ultimoEvento || ultimoEvento !== alertaData.mensaje) {
            mostrarAlertaEmergencia(alertaData.tipo, alertaData.descripcion);
            ultimoEvento = alertaData.mensaje;
        }
    } else {
        // Si hay un cambio a estado normal, limpiar el historial de alerta
        if (ultimoEvento && alertaData.mensaje === "Sistema operando normalmente") {
            ultimoEvento = null;
        }
        
        // Actualizar a estado normal
        alertaLabel.html(`<i class="fas fa-bell me-2"></i> Alerta: ${alertaData.mensaje}`);
        alertaLabel.css('color', '#2ecc71'); // Verde para estado normal
        $('.alerta-panel').removeClass('alerta-activa');
    }
}

// Mostrar alerta de emergencia
function mostrarAlertaEmergencia(tipo, descripcion) {
    console.log("¡ALERTA DE EMERGENCIA DETECTADA!:", tipo);
    
    // Configurar modal
    $('#alerta-modal-tipo').text(tipo);
    $('#alerta-modal-descripcion').text(descripcion);
    
    // Reproducir sonido
    try {
        alertaSonido.currentTime = 0;
        let playPromise = alertaSonido.play();
        
        if (playPromise !== undefined) {
            playPromise.then(() => {
                console.log("Reproduciendo sonido de alerta");
            }).catch(error => {
                console.error("Error al reproducir sonido:", error);
                // Intentar nuevamente con interacción del usuario
                $('#alertaModal').on('shown.bs.modal', function () {
                    alertaSonido.play().catch(e => console.error("Error al reproducir sonido en modal:", e));
                });
            });
        }
    } catch (error) {
        console.error("Error al manipular el audio:", error);
    }
    
    // Mostrar modal
    alertaModal.show();
    
    // Configurar tiempo para cerrar el modal y detener el sonido
    setTimeout(function() {
        if (alertaModalElement.classList.contains('show')) {
            alertaModal.hide();
        }
        try {
            alertaSonido.pause();
            alertaSonido.currentTime = 0;
        } catch (error) {
            console.error("Error al detener el sonido:", error);
        }
    }, 9000); // 9 segundos, igual que en la versión Tkinter
}

// Refrescar datos
function refrescarDatos() {
    // Animar botón de refrescar
    const btnRefrescar = $('#btn-refrescar').find('i');
    btnRefrescar.addClass('btn-refresh-animado');
    
    // Cargar eventos y actualizar estado
    cargarEventos();
    actualizarInfoEstado();
    
    // Detener animación después de la carga
    setTimeout(function() {
        btnRefrescar.removeClass('btn-refresh-animado');
    }, 1000);
}

// Mostrar mensaje de estado
function mostrarMensajeEstado(mensaje, tipo) {
    // Crear toast para notificaciones
    const toastId = 'toast-' + Date.now();
    const toast = `
        <div class="position-fixed bottom-0 end-0 p-3" style="z-index: 5">
            <div id="${toastId}" class="toast align-items-center text-white bg-${tipo} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${mensaje}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        </div>
    `;
    
    // Añadir al DOM
    $('body').append(toast);
    
    // Mostrar y configurar autodesaparición
    const toastElement = $(`#${toastId}`);
    const bsToast = new bootstrap.Toast(toastElement, { autohide: true, delay: 3000 });
    bsToast.show();
    
    // Eliminar el toast del DOM después de cerrarse
    toastElement.on('hidden.bs.toast', function () {
        $(this).parent().remove();
    });
}

// Mostrar indicador de carga
function mostrarCargando(mostrar) {
    const btnBuscar = $('#btn-buscar');
    const btnRefrescar = $('#btn-refrescar');
    
    if (mostrar) {
        btnBuscar.prop('disabled', true);
        btnRefrescar.prop('disabled', true);
        btnRefrescar.find('i').addClass('btn-refresh-animado');
    } else {
        btnBuscar.prop('disabled', false);
        btnRefrescar.prop('disabled', false);
        btnRefrescar.find('i').removeClass('btn-refresh-animado');
    }
}

// Obtener clase CSS según tipo de evento
function obtenerClaseEvento(tipo) {
    switch (tipo) {
        case 'Temperatura':
            return 'evento-temperatura';
        case 'Alerta Sismica':
            return 'evento-alerta-sismica';
        case 'Incendio':
            return 'evento-incendio';
        case 'Trafico Peatonal':
            return 'evento-trafico';
        default:
            return '';
    }
}