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
ARCHIVO_CONFIG = "config.json"

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

def cargar_config():
    try:
        with open(ARCHIVO_CONFIG, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def guardar_config(config):
    with open(ARCHIVO_CONFIG, "w") as f:
        json.dump(config, f, indent=4)

# ======== COMANDOS ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola, soy el bot que controla el tiempo de estancia.\n"
        "Usa /tiempo <días> para establecer el tiempo límite para un usuario.\n"
        "Ejemplo: /tiempo 30 → 30 días."
    )

async def tiempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /tiempo <días>")
        return

    try:
        dias = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Debe ser un número de días válido.")
        return

    usuario = update.effective_user
    chat_id = update.effective_chat.id

    # Guardar el chat_id tanto en memoria como en archivo para persistencia
    context.bot_data['chat_id'] = chat_id
    config = cargar_config()
    config['chat_id'] = chat_id
    guardar_config(config)

    datos = cargar_datos()
    datos[str(usuario.id)] = {
        "nombre": usuario.first_name,
        "fecha_ingreso": datetime.datetime.now().isoformat(),
        "dias_limite": dias
    }
    guardar_datos(datos)
    await update.message.reply_text(f"✅ Se registró a {usuario.first_name} con {dias} días de estancia.")

async def revisar_usuarios(context: ContextTypes.DEFAULT_TYPE):
    """Revisa periódicamente si hay usuarios que deben ser expulsados"""
    # Cargar chat_id desde config persistente
    config = cargar_config()
    chat_id = config.get('chat_id') or context.bot_data.get('chat_id')
    
    if not chat_id:
        print("⚠️ No hay chat_id configurado. Use /tiempo en un grupo para configurar.")
        return
    
    datos = cargar_datos()
    ahora = datetime.datetime.now()
    usuarios_a_eliminar = []

    for user_id, info in datos.items():
        fecha = datetime.datetime.fromisoformat(info["fecha_ingreso"])
        limite = fecha + datetime.timedelta(days=info["dias_limite"])
        if ahora >= limite:
            usuarios_a_eliminar.append(user_id)

    for user_id in usuarios_a_eliminar:
        try:
            await context.bot.ban_chat_member(chat_id, int(user_id))
            await context.bot.send_message(chat_id, f"⏰ El tiempo de {datos[user_id]['nombre']} ha expirado. Fue removido.")
            print(f"✅ Usuario {user_id} removido del chat {chat_id}")
            del datos[user_id]
        except Exception as e:
            print(f"❌ Error al eliminar usuario {user_id}: {e}")

    if usuarios_a_eliminar:
        guardar_datos(datos)

# ======== FUNCIÓN PRINCIPAL ========
def main():
    if not TOKEN:
        print("❌ ERROR: No se encontró el token BOT_TOKEN. Configúralo en los Secrets o variables de entorno.")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    
    # Cargar configuración persistente al iniciar
    config = cargar_config()
    if 'chat_id' in config:
        app.bot_data['chat_id'] = config['chat_id']
        print(f"📍 Chat ID cargado desde configuración: {config['chat_id']}")
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tiempo", tiempo))

    # Configurar tarea periódica para revisar usuarios cada hora
    job_queue = app.job_queue
    job_queue.run_repeating(revisar_usuarios, interval=3600, first=10)

    print("🤖 Bot iniciado correctamente...")
    print("⏰ Revisión automática de usuarios configurada cada hora")
    app.run_polling()

if __name__ == "__main__":
    main()

