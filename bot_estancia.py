import os
import json
import asyncio
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ============================================================
# ⚙️ Cargar variables de entorno (.env)
# ============================================================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ ERROR: No se encontró el token BOT_TOKEN. Verifica tu archivo .env")
    exit()

# ============================================================
# 🗂️ Archivo donde se guardan los datos de usuarios
# ============================================================
ARCHIVO_DATOS = "usuarios.json"


# ============================================================
# 🧠 Funciones de carga y guardado de datos
# ============================================================
def cargar_datos():
    try:
        with open(ARCHIVO_DATOS, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w") as f:
        json.dump(datos, f, indent=4)


# ============================================================
# 👋 Comando /start — Registrar usuario
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("⚠️ Se recibió un evento sin mensaje en /start")
        return

    user = update.effective_user
    datos = cargar_datos()

    if str(user.id) not in datos:
        datos[str(user.id)] = {"nombre": user.first_name, "tiempo": 0}
        guardar_datos(datos)

    await update.message.reply_text(
        f"👋 ¡Hola {user.first_name}! Bienvenido al bot de estancia.\n"
        f"Usa /tiempo para ver tu tiempo o /editar para modificarlo."
    )


# ============================================================
# ⏱️ Comando /tiempo — Mostrar tiempo de usuario
# ============================================================
async def tiempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("⚠️ Se recibió un evento sin mensaje en /tiempo")
        return

    user_id = str(update.effective_user.id)
    datos = cargar_datos()

    if user_id in datos:
        tiempo = datos[user_id]["tiempo"]
        await update.message.reply_text(f"⏱ Tu tiempo actual es de {tiempo} minutos.")
    else:
        await update.message.reply_text("❌ No estás registrado aún. Usa /start primero.")


# ============================================================
# ✏️ Comando /editar — Modificar tiempo de estancia
# ============================================================
async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        print("⚠️ Se recibió un evento sin mensaje en /editar")
        return

    user_id = str(update.effective_user.id)
    datos = cargar_datos()

    if user_id not in datos:
        await update.message.reply_text("❌ No estás registrado. Usa /start primero.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("✏️ Usa el comando así: /editar 30 (para 30 minutos)")
        return

    try:
        nuevo_tiempo = int(context.args[0])
        datos[user_id]["tiempo"] = nuevo_tiempo
        guardar_datos(datos)
        await update.message.reply_text(f"✅ Tiempo actualizado a {nuevo_tiempo} minutos.")
    except ValueError:
        await update.message.reply_text("⚠️ Por favor ingresa un número válido.")


# ============================================================
# 🚀 MAIN — Inicializa el bot
# ============================================================
async def main():
    print("✅ Iniciando bot de Telegram...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Registrar comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tiempo", tiempo))
    app.add_handler(CommandHandler("editar", editar))

    print("✅ Bot iniciado... Esperando mensajes.")
    await app.run_polling()


# ============================================================
# 🧩 Ejecutar con compatibilidad para Python 3.12 / PM2
# ============================================================
if __name__ == "__main__":
    nest_asyncio.apply()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            print("⚙️ Loop ya en ejecución, creando tarea...")
            loop.create_task(main())
            loop.run_forever()
        else:
            print("✅ Iniciando nuevo loop de eventos...")
            loop.run_until_complete(main())
    except RuntimeError:
        print("🔄 Reintentando con nuevo loop...")
        asyncio.run(main())

