import os
import sys
import json
import asyncio
import nest_asyncio
import psutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, ConversationHandler
)

# ============================================================
# 🛡️ Evitar ejecución duplicada
# ============================================================
def check_already_running():
    current_pid = os.getpid()
    script_name = os.path.basename(__file__)
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['pid'] != current_pid and proc.info['cmdline'] and script_name in " ".join(proc.info['cmdline']):
                print(f"⚠️ Ya hay otra instancia del bot ejecutándose (PID {proc.info['pid']}).")
                sys.exit()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

check_already_running()

# ============================================================
# ⚙️ Configuración
# ============================================================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # ej. "4442684304"
ROOT_PASS = os.getenv("ROOT_PASS")  # ej. "73612257"

ARCHIVO_DATOS = "usuarios.json"

if not TOKEN:
    print("❌ ERROR: Falta BOT_TOKEN en el archivo .env")
    sys.exit()

# ============================================================
# 📁 Datos
# ============================================================
def cargar_datos():
    try:
        if not os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
                json.dump({"admins": [ADMIN_ID] if ADMIN_ID else [], "usuarios": {}}, f)
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "admins" not in data:
                data["admins"] = [ADMIN_ID] if ADMIN_ID else []
            if "usuarios" not in data:
                data["usuarios"] = {}
            return data
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return {"admins": [ADMIN_ID] if ADMIN_ID else [], "usuarios": {}}

def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

# ============================================================
# ⏱️ Utilidades de tiempo
# ============================================================
def formato_tiempo(segundos: int) -> str:
    segundos = int(segundos)
    años = segundos // (365 * 24 * 3600)
    segundos %= 365 * 24 * 3600
    meses = segundos // (30 * 24 * 3600)
    segundos %= 30 * 24 * 3600
    dias = segundos // (24 * 3600)
    segundos %= 24 * 3600
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    return f"{años}a {meses}m {dias}d {horas}h {minutos}m {segs}s"

def convertir_a_segundos(entrada: str) -> int:
    entrada = entrada.lower().replace(" ", "")
    años = meses = dias = segundos = 0
    num = ""
    for c in entrada:
        if c.isdigit():
            num += c
        elif c == "a":
            años = int(num or 0); num = ""
        elif c == "m":
            meses = int(num or 0); num = ""
        elif c == "d":
            dias = int(num or 0); num = ""
        elif c == "s":
            segundos = int(num or 0); num = ""
    total = años * 365 * 24 * 3600 + meses * 30 * 24 * 3600 + dias * 24 * 3600 + segundos
    return total

# ============================================================
# 👑 Control de admins
# ============================================================
def es_admin(user_id: str) -> bool:
    datos = cargar_datos()
    return user_id in datos.get("admins", [])

def solo_admin(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        if not es_admin(str(update.effective_user.id)):
            await update.message.reply_text("❌ No tienes permisos para usar este comando.")
            return
        return await func(update, context)
    return wrapper

# ============================================================
# ⏱️ /tg — Mostrar tiempo
# ============================================================
async def tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    datos = cargar_datos()
    usuarios = datos.setdefault("usuarios", {})

    if str(user.id) not in usuarios:
        usuarios[str(user.id)] = {"nombre": user.first_name or "Usuario", "tiempo": 0}
        guardar_datos(datos)

    tiempo_seg = usuarios[str(user.id)]["tiempo"]
    await context.bot.send_message(chat_id=user.id, text=f"⏱ Tu tiempo actual es: {formato_tiempo(tiempo_seg)}")

# ============================================================
# 📋 /lista — Solo admins
# ============================================================
@solo_admin
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = cargar_datos()
    usuarios = datos.get("usuarios", {})
    admins = set(datos.get("admins", []))

    if not usuarios:
        await context.bot.send_message(chat_id=update.effective_user.id, text="📂 No hay usuarios registrados.")
        return

    mensaje = "<b>📜 Lista de usuarios</b>\n\n"
    for uid, info in usuarios.items():
        nombre = info.get("nombre", "Desconocido")
        t = int(info.get("tiempo", 0))
        ttxt = formato_tiempo(t)
        if uid in admins:
            mensaje += f"👑 <b>{nombre}</b> ({uid}) → {ttxt}\n"
        else:
            mensaje += f"👤 {nombre} ({uid}) → {ttxt}\n"

    await context.bot.send_message(chat_id=update.effective_user.id, text=mensaje, parse_mode="HTML")

# ============================================================
# 🚀 MAIN
# ============================================================
async def main():
    print("✅ Iniciando bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("tg", tg))
    app.add_handler(CommandHandler("lista", lista))

    print("🤖 Bot en ejecución. Esperando comandos...")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())


