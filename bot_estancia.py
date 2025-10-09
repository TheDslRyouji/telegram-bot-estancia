import os
import sys
import json
import asyncio
import nest_asyncio
import psutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ============================================================
# 🛡️ Protección: evitar que el bot se ejecute dos veces
# ============================================================
def check_already_running():
    current_pid = os.getpid()
    script_name = os.path.basename(__file__)
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['pid'] != current_pid and proc.info['cmdline'] and script_name in " ".join(proc.info['cmdline']):
                print(f"⚠️ Ya hay otra instancia del bot ejecutándose (PID {proc.info['pid']}). Cerrando esta...")
                sys.exit()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

check_already_running()

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

def formato_tiempo(segundos):
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    return f"{horas}h {minutos}m {segs}s"


# ============================================================
# 👋 /start — Registrar usuario
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    datos = cargar_datos()

    if str(user.id) not in datos:
        datos[str(user.id)] = {"nombre": user.first_name, "tiempo": 0}
        guardar_datos(datos)

    await update.message.reply_text(
        f"👋 ¡Hola {user.first_name}! Bienvenido al bot de estancia.\n"
        "Usa /tiempo para ver tu tiempo o /editar para modificarlo.\n"
        "Ejemplo: /editar 1h30m20s o /editar 45m o /editar 120s"
    )


# ============================================================
# ⏱️ /tiempo — Mostrar tiempo
# ============================================================
async def tiempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = str(update.effective_user.id)
    datos = cargar_datos()

    if user_id in datos:
        total_segundos = datos[user_id]["tiempo"]
        tiempo_legible = formato_tiempo(total_segundos)
        await update.message.reply_text(f"⏱ Tu tiempo actual es de {tiempo_legible}.")
    else:
        await update.message.reply_text("❌ No estás registrado aún. Usa /start primero.")


# ============================================================
# ✏️ /editar — Modificar tiempo (h, m o s)
# ============================================================
async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = str(update.effective_user.id)
    datos = cargar_datos()

    if user_id not in datos:
        await update.message.reply_text("❌ No estás registrado. Usa /start primero.")
        return

    if not context.args:
        await update.message.reply_text("✏️ Usa el comando así: /editar 1h30m o /editar 45m o /editar 90s")
        return

    entrada = context.args[0].lower()

    # Convertir formato flexible a segundos
    try:
        horas = minutos = segundos = 0
        num = ""
        for c in entrada:
            if c.isdigit():
                num += c
            elif c == 'h':
                horas = int(num)
                num = ""
            elif c == 'm':
                minutos = int(num)
                num = ""
            elif c == 's':
                segundos = int(num)
                num = ""
        total_segundos = horas * 3600 + minutos * 60 + segundos

        if total_segundos <= 0:
            await update.message.reply_text("⚠️ Ingresa un valor válido mayor que 0.")
            return

        datos[user_id]["tiempo"] = total_segundos
        guardar_datos(datos)

        await update.message.reply_text(
            f"✅ Tiempo actualizado a {formato_tiempo(total_segundos)}."
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error al procesar el tiempo: {e}")


# ============================================================
# 🚀 MAIN
# ============================================================
async def main():
    print("✅ Iniciando bot de Telegram...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tiempo", tiempo))
    app.add_handler(CommandHandler("editar", editar))

    print("✅ Bot iniciado... Esperando mensajes.")
    await app.run_polling()


# ============================================================
# 🧩 Ejecutar
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

