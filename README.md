# TV FULL PRO — Eventos y agenda deportiva

Repositorio **público**, separado de la aplicación privada. Publica solamente metadatos de eventos e imágenes de uso autorizado. **Nunca almacena enlaces IPTV, listas M3U, contraseñas ni claves de reproducción.**

## Enlace que consulta la APK

`https://raw.githubusercontent.com/luchochavezfacebook-byte/TVFULL-EVENTOS/main/eventos.json`

La aplicación V61 puede consultar este archivo y presentar **máximo ocho eventos** que coincidan con canales disponibles en las listas del cliente. El reproductor recibe la URL de la lista del dispositivo, **no del JSON**. Las novedades remotas no requieren compilar otra APK.

## Estructura única

| Archivo | Propósito |
|---|---|
| `eventos.json` | **Único archivo publicado** que consume la APK. Lo genera la automatización. |
| `config/manuales.json` | Entradas que administramos nosotros: horarios, nombre, canales y banners propios. Estas entradas tienen prioridad. |
| `imagenes/` | Banners originales o con permiso de uso. Recomendado WebP horizontal 16:9. |
| `scripts/actualizar_agenda.py` | Consulta la agenda pública de [Olé](https://www.ole.com.ar/agenda-deportiva), interpreta horarios y señales de TV, combina con los manuales. |
| `scripts/validar_eventos.py` | Confirma compatibilidad, límites e impide enlaces de streaming en el JSON. |
| `.github/workflows/actualizar-agenda.yml` | Actualización cada cuatro horas o manual, **sin compilar APK**. |
| `tests/` | Pruebas aisladas de extracción y deduplicación. |

## Cómo cargar un evento propio

1. Editar `config/manuales.json` en GitHub. Agregar un objeto al array `events` con `id`, `title`, `image`, `starts_at`, `show_from`, `show_until` y `channel_names`.
2. Subir el banner a `imagenes/` con nombre propio, en WebP/JPG/PNG, **sin fotografías de terceros sin autorización**.
3. Desde **Actions → Actualizar agenda deportiva TV FULL PRO → Run workflow**, ejecutar una sincronización (o dejar que lo haga automáticamente).
4. Consultar `eventos.json` para verificar el resultado.

Ejemplo de nombre de canal: `"channel_names": ["SPEN"]`. Solo declaramos señales verificadas para ese evento. La APK solo mostrará el evento si localiza alguna de esas señales **entre los canales reales del cliente**, y respeta el control parental.

## Agenda de Olé: límites honestos

- El extractor utiliza **hechos deportivos** (equipos, horarios y señales publicadas) y no copia artículos, imágenes ni logos de Olé.
- Importa solo encuentros cuya hora, equipos y canal lineal se puedan identificar con certeza. Excluye plataformas exclusivamente de streaming como DGO/Disney+ si no hay un canal lineal reconocido.
- Olé no garantiza una API pública para este uso. Si bloquea el acceso o cambia el HTML, el workflow **falla sin sobrescribir el último `eventos.json` válido**. Se pueden seguir cargando eventos manualmente; no se presenta el error como una actualización exitosa.
- La hora es Argentina (`America/Argentina/Buenos_Aires`, `-03:00`). Los eventos vencidos dejan de mostrarse en la APK; el script los retira en una actualización posterior.
- Tope del protocolo: **120 eventos en el archivo; hasta 8 visibles a la vez**. El menú de canales sigue cargándose exclusivamente desde las listas IPTV.

## Seguridad y derechos de uso

El repositorio es público. No agregar URLs M3U/Xtream, nombres de usuario, cookies, tokens, credenciales ni contenido privado. El banner preinstalado fue creado para TV FULL PRO; **no se incluye la fotografía editorial de Olé** en el repositorio público. La información deportiva debe contrastarse con las fuentes oficiales cuando sea importante.
