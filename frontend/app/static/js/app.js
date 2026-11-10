// Métodos auxiliares para la interfaz Web
//Flujo: el usuario envía el formulario -> pedimos el PDF con fetch ->
// lo mostramos en un iframe -> el botón "Descargar PDF" reutiliza ese mismo archivo.

const formulario = document.getElementById('form-factura');
const inputFactura = document.getElementById('id_factura');
const btnGenerar = document.getElementById('btn-generar');
const mensaje = document.getElementById('mensaje');
const contenedor = document.getElementById('contenedor');
const vistaPrevia = document.getElementById('vista-previa');
const tituloVistaPrevia = document.getElementById('titulo-vista-previa');
const visorPdf = document.getElementById('visor-pdf');
const btnDescargar = document.getElementById('btn-descargar');

//Guardamos la URL temporal del PDF actual para poder liberarla después
let urlPdfActual = null;

//Traduce el código de estado HTTP a un mensaje que el usuario entienda
function mensajeDeError(status) {
    switch (status) {
        case 404: return 'No se encontró la factura. Revisa el ID e inténtalo de nuevo.';
        case 503: return 'El servicio de facturas no está disponible. Verifica que el backend esté corriendo.';
        default:  return `No se pudo generar la factura (error ${status}). Inténtalo de nuevo.`;
    }
}

function mostrarError(texto) {
    mensaje.textContent = texto;
    mensaje.hidden = false;
}

function ocultarError() {
    mensaje.hidden = true;
    mensaje.textContent = '';
}

function setCargando(cargando) {
    btnGenerar.disabled = cargando;
    btnGenerar.textContent = cargando ? 'Generando…' : 'Generar Factura';
}

function mostrarVistaPrevia(blob, idFactura) {
    //Liberar la URL anterior para no acumular PDFs en memoria
    if (urlPdfActual) {
        URL.revokeObjectURL(urlPdfActual);
    }

    //Crear una URL temporal (blob:...) que apunta al PDF guardado en memoria
    urlPdfActual = URL.createObjectURL(blob);

    //La vista previa y la descarga usan EL MISMO archivo
    visorPdf.src = urlPdfActual;
    btnDescargar.href = urlPdfActual;
    btnDescargar.download = `factura_${idFactura}.pdf`;

    tituloVistaPrevia.textContent = `Vista previa: ${idFactura}`;
    vistaPrevia.hidden = false;
    contenedor.classList.add('con-vista-previa');
}

formulario.addEventListener('submit', async (evento) => {
    //Evita que el navegador cambie de página (comportamiento normal de un form)
    evento.preventDefault();

    const idFactura = inputFactura.value.trim();
    if (!idFactura) {
        mostrarError('Escribe un ID de factura.');
        return;
    }

    ocultarError();
    setCargando(true);

    try {
        //FormData empaqueta los campos igual que lo haría el formulario normal,
        //así Flask sigue leyendo request.form['id_factura'] sin cambios
        const respuesta = await fetch('/generar-pdf', {
            method: 'POST',
            body: new FormData(formulario),
        });

        if (!respuesta.ok) {
            mostrarError(mensajeDeError(respuesta.status));
            return;
        }

        //blob() = leer la respuesta como datos binarios (el PDF), no como texto
        const pdf = await respuesta.blob();
        mostrarVistaPrevia(pdf, idFactura);

    } catch (error) {
        //fetch solo lanza excepción si no hubo respuesta (servidor caído, sin red)
        mostrarError('No hay conexión con el servidor. Verifica que los servicios estén levantados.');
        console.error(error);
    } finally {
        //finally se ejecuta siempre: con éxito, con error o con return
        setCargando(false);
    }
});
