# 🤖 Telegram Bot — Control de Estancia y Expulsión Automática

Bot de Telegram creado para **controlar el tiempo de estancia de los usuarios en grupos**.  
Permite registrar usuarios por segundos, minutos, horas o días, y los expulsa automáticamente cuando su tiempo expira.

---

## 🧠 Funcionalidades principales

✅ Registrar usuarios con tiempo personalizado  
✅ Editar tiempo de estancia  
✅ Ver lista de usuarios y tiempo restante  
✅ Expulsar automáticamente a los que superan su tiempo  
✅ Soporte para segundos, minutos, horas y días  
✅ Compatible con grupos y chats privados  
✅ Compatible con Replit (mantiene ejecución continua)

---

## 💬 Comandos disponibles

| Comando | Descripción | Ejemplo |
|----------|--------------|---------|
| `/start` | Muestra mensaje de bienvenida | `/start` |
| `/tiempo <duración> [nombre]` | Registra un usuario y tiempo | `/tiempo 5m Juan` |
| `/editar <duración> <nombre>` | Edita el tiempo de un usuario existente | `/editar 2h Juan` |
| `/ver` | Muestra todos los usuarios registrados y su tiempo restante | `/ver` |

🕒 **Unidades disponibles:**
- `s` → segundos  
- `m` → minutos  
- `h` → horas  
- `d` → días  

📘 Ejemplos:
