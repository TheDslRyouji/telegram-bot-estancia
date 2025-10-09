import os
import json
import datetime
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ======== CONFIGURACIÓN ========
TOKEN = "AQUI_TU_TOKEN_DEL_BOT"
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
    datos = cargar_datos()
    datos[str(usuario.id)] = {
        "nombre": usuario.first_name,
        "fecha_ingreso": datetime.datetime.now().isoformat(),
        "dias_limite": dias
    }
    guardar_datos(datos)
    await update.message.reply_text(f"✅ Se registró a {usuario.first_name} con {dias} días de estancia.")

async def revisar_usuarios(app):
    while True:
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
                chat_id = app.chat_id  # opcional si el bot está en un grupo fijo
                await app.bot.ban_chat_member(chat_id, int(user_id))
                await app.bot.send_message(chat_id, f"⏰ El tiempo de {datos[user_id]['nombre']} ha expirado. Fue removido.")
                del datos[user_id]
            except Exception as e:
                print(f"Error al eliminar usuario {user_id}: {e}")

        guardar_datos(datos)
        await asyncio.sleep(3600)  # revisar cada hora

# ======== FUNCIÓN PRINCIPAL ========
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tiempo", tiempo))
    print("🤖 Bot iniciado...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
