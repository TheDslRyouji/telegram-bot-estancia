import json
import datetime
import asyncio
import os
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ======== CONFIGURACIÓN ========
nest_asyncio.apply()
TOKEN = os.getenv("BOT_TOKEN")   # 🔐 Se obtiene desde Secrets en Replit o variable de entorno
ARCHIVO_DATOS = "usuarios.json"

# ======== FUNCIONES DE GUARDADO ========
def cargar_datos():
    try:
        with open(ARCHIVO_DATOS, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w") as f:
        json.dump(datos, f, indent=4)

# ======== FUNCIÓN AUXILIAR ========
def convertir_tiempo(valor: str) -> datetime.timedelta:
    """Convierte texto como 10s, 5m, 2h, 3d a timedelta."""
    unidad = valor[-1].lower()
    cantidad = int(valor[:-1])
    if unidad == "s":
        return datetime.timedelta(seconds=cantidad)
    elif unidad == "m":
        return datetime.timedelta(minutes=cantidad)
    elif unidad == "h":
        return datetime.timedelta(hours=cantidad)
    elif unidad == "d":
        return datetime.timedelta(days=cantidad)
    else:
        raise ValueError("Formato inválido. Usa s, m, h o d.")

# ======== COMANDOS ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola, soy el bot de control de estancia.\n\n"
        "Usa /tiempo <duración> <nombre_opcional>\n"
        "Ejemplo:\n"
        "• /tiempo 30s Juan\n"
        "• /tiempo 10m Ana\n"
        "• /tiempo 2h Pedro\n"
        "• /tiempo 3d (tu propio nombre)"
    )

async def tiempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /tiempo <duración> [nombre_opcional]\nEjemplo: /tiempo 5m Juan")
        return

    try:
        tiempo_str = context.args[0]
        delta = convertir_tiempo(tiempo_str)
    except Exception:
        await update.message.reply_text("⚠️ Formato inválido. Usa por ejemplo: 10s, 5m, 2h o 3d.")
        return

    nombre = " ".join(context.args[1:]) if len(context.args) > 1 else update.effective_user.first_name
    usuario = update.effective_user
    chat_id = update.effective_chat.id
    context.bot_data["chat_id"] = chat_id

    datos = cargar_datos()
    datos[str(usuario.id)] = {
        "nombre": nombre,
        "fecha_ingreso": datetime.datetime.now().isoformat(),
        "duracion_segundos": delta.total_seconds(),
        "chat_id": chat_id
    }
    guardar_datos(datos)

    await update.message.reply_text(f"✅ Se registró a *{nombre}* por {tiempo_str}.", parse_mode="Markdown")

async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /editar <duración> <nombre>")
        return

    try:
        tiempo_str = context.args[0]
        delta = convertir_tiempo(tiempo_str)
    except Exception:
        await update.message.reply_text("⚠️ Formato inválido. Usa por ejemplo: 10s, 5m, 2h o 3d.")
        return

    nombre = " ".join(context.args[1:])
    datos = cargar_datos()
    encontrado = False

    for user_id, info in datos.items():
        if info["nombre"].lower() == nombre.lower():
            info["fecha_ingreso"] = datetime.datetime.now().isoformat()
            info["duracion_segundos"] = delta.total_seconds()
            encontrado = True
            break

    if encontrado:
        guardar_datos(datos)
        await update.message.reply_text(f"✏️ Se actualizó el tiempo de *{nombre}* a {tiempo_str}.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ No se encontró a {nombre} en la lista.")

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = cargar_datos()
    if not datos:
        await update.message.reply_text("📭 No hay usuarios registrados.")
        return

    ahora = datetime.datetime.now()
    texto = "🕒 *Tiempos de estancia actuales:*\n\n"
    for info in datos.values():
        fecha = datetime.datetime.fromisoformat(info["fecha_ingreso"])
        restante = fecha + datetime.timedelta(seconds=info["duracion_segundos"]) - ahora
        if restante.total_seconds() > 0:
            texto += f"• {info['nombre']}: {str(restante).split('.')[0]} restantes\n"
        else:
            texto += f"• {info['nombre']}: ⏰ Expirado\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# ======== REVISIÓN AUTOMÁTICA ========
async def revisar_usuarios(context: ContextTypes.DEFAULT_TYPE):
    datos = cargar_datos()
    ahora = datetime.datetime.now()
    usuarios_a_eliminar = []

    for user_id, info in list(datos.items()):
        fecha = datetime.datetime.fromisoformat(info["fecha_ingreso"])
        limite = fecha + datetime.timedelta(seconds=info["duracion_segundos"])
        if ahora >= limite:
            usuarios_a_eliminar.append(user_id)

    for user_id in usuarios_a_eliminar:
        try:
            chat_id = datos[user_id].get("chat_id", context.bot_data.get("chat_id"))
            nombre = datos[user_id]["nombre"]
            await context.bot.send_message(chat_id, f"⏰ El tiempo de *{nombre}* ha expirado.", parse_mode="Markdown")

            # 🚨 Expulsar al usuario del grupo
            await context.bot.ban_chat_member(chat_id, int(user_id))
            await asyncio.sleep(1)
            await context.bot.unban_chat_member(chat_id, int(user_id))  # lo desbanea para permitir que vuelva si desea

            print(f"✅ Usuario expulsado: {nombre} ({user_id})")
            del datos[user_id]
        except Exception as e:
            print(f"❌ Error al expulsar {user_id}: {e}")

    if usuarios_a_eliminar:
        guardar_datos(datos)

# ======== FUNCIÓN PRINCIPAL ========
async def main():
    if not TOKEN:
        print("❌ ERROR: No se encontró el token BOT_TOKEN.")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tiempo", tiempo))
    app.add_handler(CommandHandler("editar", editar))
    app.add_handler(CommandHandler("ver", ver))

    # Revisa cada 10 segundos (ajústalo a 3600 = cada hora)
    job_queue = app.job_queue
    job_queue.run_repeating(revisar_usuarios, interval=10, first=10)

    print("🤖 Bot iniciado correctamente...")
    print("🧹 Revisión automática de usuarios activa.")
    await app.run_polling()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
