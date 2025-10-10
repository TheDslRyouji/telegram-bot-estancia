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
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            data = json.load(f)
            # normalizar estructura si faltan claves
            if "admins" not in data:
                data["admins"] = [ADMIN_ID] if ADMIN_ID else []
            if "usuarios" not in data:
                data["usuarios"] = {}
            return data
    except FileNotFoundError:
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
            return  # silencioso
        return await func(update, context)
    return wrapper

# ============================================================
# ⏱️ /tg — Mostrar tiempo (privado al usuario)
# ============================================================
async def tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    datos = cargar_datos()
    usuarios = datos.setdefault("usuarios", {})

    if str(user.id) not in usuarios:
        usuarios[str(user.id)] = {"nombre": user.first_name or "Usuario", "tiempo": 0}
        guardar_datos(datos)

    tiempo_seg = usuarios[str(user.id)]["tiempo"]
    # siempre responder en privado
    await context.bot.send_message(chat_id=user.id, text=f"⏱ Tu tiempo actual es: {formato_tiempo(tiempo_seg)}")

# ============================================================
# 📋 /lista — Solo admins, con colores (verde→naranja) y admins en azul
# ============================================================
@solo_admin
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos = cargar_datos()
    usuarios = datos.get("usuarios", {})
    admins = set(datos.get("admins", []))

    if not usuarios:
        await context.bot.send_message(chat_id=update.effective_user.id, text="📂 No hay usuarios.")
        return

    # 90 días como referencia para el degradado
    tiempo_ref = 90 * 24 * 3600

    def color_gradiente(segundos):
        # ratio 0..1
        ratio = max(0, min(segundos / tiempo_ref, 1))
        # Verde (0,204,102) -> Naranja (217,140,51)
        r = int(0 + (217 - 0) * (1 - ratio))
        g = int(204 * ratio + 140 * (1 - ratio))
        b = int(102 * ratio + 51 * (1 - ratio))
        return f"#{r:02x}{g:02x}{b:02x}"

    # ordenar por tiempo desc
    items = sorted(usuarios.items(), key=lambda kv: kv[1].get("tiempo", 0), reverse=True)

    mensaje = "<b>📜 Lista de usuarios y tiempos</b>\n\n"
    for uid, info in items:
        nombre = info.get("nombre", "Desconocido")
        t = int(info.get("tiempo", 0))
        ttxt = formato_tiempo(t)

        if uid in admins:
            # Admin en azul y negrita
            mensaje += f"👑 <b><span style='color:#00aaff'>{nombre}</span></b> ({uid}) → {ttxt}\n"
        else:
            col = color_gradiente(t)
            mensaje += f"👤 <span style='color:{col}'>{nombre}</span> ({uid}) → {ttxt}\n"

    await context.bot.send_message(chat_id=update.effective_user.id, text=mensaje, parse_mode="HTML")

# ============================================================
# 🔐 /sudosu — flujo seguro (ID + contraseña + valor), redirige a privado si se lanza en grupo
# ============================================================
ASK_ID, ASK_PASS, ASK_VAL = range(3)

async def sudosu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # Solo admin principal puede iniciar
    if str(user.id) != str(ADMIN_ID):
        return  # silencioso

    # Si se invoca en grupo/canal, redirigir a privado
    if chat.type != "private":
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="🔒 Has usado /sudosu en un grupo. Continúa aquí en privado."
            )
            try:
                await update.message.delete()
            except:
                pass
        except:
            # Si el bot no puede escribir en tu privado
            await update.message.reply_text("📩 Primero abre un chat privado conmigo para comandos seguros.")
        return ConversationHandler.END

    await update.message.reply_text("🔒 Modo sudosu: escribe tu ID (solo número).")
    return ASK_ID

async def sudosu_ask_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user

    # borrar mensaje con el ID
    try: await msg.delete()
    except: pass

    context.user_data["root_id_input"] = (msg.text or "").strip()
    await context.bot.send_message(chat_id=user.id, text="🔒 Ahora escribe la contraseña.")
    return ASK_PASS

async def sudosu_ask_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user

    # borrar mensaje con la contraseña
    try: await msg.delete()
    except: pass

    context.user_data["root_pass_input"] = (msg.text or "").strip()
    await context.bot.send_message(chat_id=user.id, text="🔒 Por último, escribe el valor (ej. +5d, 1a2m, -30s).")
    return ASK_VAL

async def sudosu_ask_val(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user

    # borrar mensaje con el valor (opcional)
    try: await msg.delete()
    except: pass

    valor = (msg.text or "").strip()
    root_id_input = context.user_data.get("root_id_input", "")
    root_pass_input = context.user_data.get("root_pass_input", "")

    # Validación contra .env
    if root_id_input != str(ADMIN_ID) or root_pass_input != str(ROOT_PASS):
        context.user_data.clear()
        return ConversationHandler.END

    entrada = valor.lower().replace(" ", "")
    op = "set"
    if entrada.startswith("+"):
        op = "sum"; entrada = entrada[1:]
    elif entrada.startswith("-"):
        op = "rest"; entrada = entrada[1:]

    total = convertir_a_segundos(entrada)
    if total <= 0:
        context.user_data.clear()
        return ConversationHandler.END

    datos = cargar_datos()
    usuarios = datos.setdefault("usuarios", {})
    uid = str(ADMIN_ID)
    if uid not in usuarios:
        usuarios[uid] = {"nombre": "AdminRoot", "tiempo": 0}

    tiempo_act = int(usuarios[uid].get("tiempo", 0))
    if op == "sum":
        nuevo = tiempo_act + total
    elif op == "rest":
        nuevo = max(0, tiempo_act - total)
    else:
        nuevo = total

    usuarios[uid]["tiempo"] = nuevo
    guardar_datos(datos)

    # Confirmación privada solo para el admin principal
    await context.bot.send_message(
        chat_id=int(ADMIN_ID),
        text=f"🔒 Modo sudosu: tiempo actualizado.\nNuevo total: {formato_tiempo(nuevo)}"
    )

    context.user_data.clear()
    return ConversationHandler.END

async def sudosu_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    context.user_data.clear()
    return ConversationHandler.END

# ============================================================
# 🚀 MAIN
# ============================================================
async def main():
    print("✅ Iniciando bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Comandos públicos/administrativos
    app.add_handler(CommandHandler("tg", tg))
    app.add_handler(CommandHandler("lista", lista))  # solo admins (decorador)

    # Conversación /sudosu
    sudosu_conv = ConversationHandler(
        entry_points=[CommandHandler("sudosu", sudosu_start)],
        states={
            ASK_ID: [MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, sudosu_ask_id)],
            ASK_PASS: [MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, sudosu_ask_pass)],
            ASK_VAL: [MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, sudosu_ask_val)],
        },
        fallbacks=[CommandHandler("cancel", sudosu_cancel)],
        conversation_timeout=60,
    )
    app.add_handler(sudosu_conv)

    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())

