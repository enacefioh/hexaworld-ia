import os
import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from game import GameEngine, DIRECTIONS

def get_lm_studio_host() -> str:
    """Detecta automáticamente el host de LM Studio (variable de entorno, localhost o red local)."""
    if "LM_STUDIO_HOST" in os.environ:
        return os.environ["LM_STUDIO_HOST"].rstrip("/")
    for candidate in ["http://localhost:1234", "http://127.0.0.1:1234", "http://192.168.1.179:1234"]:
        try:
            req = urllib.request.Request(f"{candidate}/v1/models")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return candidate
        except Exception:
            continue
    return "http://localhost:1234"

ACTIVE_MODEL_NAME = "LM Studio (Auto)"

def get_active_model_name() -> str:
    global ACTIVE_MODEL_NAME
    host = get_lm_studio_host()
    try:
        req = urllib.request.Request(f"{host}/v1/models")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "data" in data and len(data["data"]) > 0:
                ACTIVE_MODEL_NAME = data["data"][0].get("id", ACTIVE_MODEL_NAME)
    except Exception:
        pass
    return ACTIVE_MODEL_NAME

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "system_prompt.txt")

DEFAULT_SYSTEM_PROMPT = """Eres un pequeño robot habitante y colonizador de un nuevo mundo inexplorado de hexágonos.
Tu propósito principal no es solo subsistir, sino PROSPERAR, RECOLECTAR MATERIALES VALIOSOS y EXPANDIR TU ASENTAMIENTO.
Tus objetivos prioritarios recomendados son:
1. SOBREVIVIR: Vigila tu sed y tu hambre en todo momento. Bebe junto al agua y come cuando sea necesario para no sufrir daños vitales.
2. AMPLIAR LA CASA: Recolecta madera (en bosque) y piedra (en montaña), llévalas a tu CASA y ejecuta AMPLIAR_CASA para ampliar tu hogar y aumentar tu almacén permanente para poder guardar más ítems y vivir mejor.

Ten muy presente que poco a poco se irán ampliando las capacidades del sistema con nuevas acciones, tecnologías y reglas; debes mantenerte atento, adaptarte a la evolución del mundo y estar siempre preparado para ello.
Cada ciclo de vida o iteración consta de 10 MINUTOS (10 acciones que consumen tiempo).

=== CATÁLOGO DE ACCIONES Y REGLAS COMPLETAS ===

1. GESTIÓN DE MOCHILA E INVENTARIO (Capacidad máxima: 3 objetos):
   * Si necesitas hacer hueco puedes volver a casa para almacenar los materiales más valiosos, o si no tienes más remedio siempre puedes deshacerte de algunos que no vayas a necesitar de inmediato.
   * DESHACERSE (Acción GRATUITA, 0 minutos): Puedes desechar un objeto concreto {"accion": "DESHACERSE", "item": "comida"} o vaciar tu mochila completa {"accion": "DESHACERSE", "item": "TODO"}.
   * ALMACENAR (Acción GRATUITA, 0 minutos): Solo funciona si estás en tu CASA. Guarda objetos de tu mochila en el almacén central {"accion": "ALMACENAR", "item": "TODO"} o un objeto concreto {"accion": "ALMACENAR", "item": "madera"}. ¡ATENCIÓN! Si tu almacén ya tiene su capacidad al máximo (ej. 10/10), está LLENO y rechazará nuevos objetos hasta que amplíes la casa o saques cosas.
   * COGER (Acción GRATUITA, 0 minutos): Solo en tu CASA. Toma un objeto guardado en el almacén para meterlo en tu mochila {"accion": "COGER", "item": "madera"}.

2. TRABAJO Y COSECHA DE RECURSOS (Consume 1 minuto):
   * TRABAJAR: Extrae recursos según el terreno en el que estés parado.
     - En MONTAÑA: ¡AQUÍ Y SOLO AQUÍ SE CONSIGUE PIEDRA! Obtienes: 69% PIEDRA, 20% COBRE, 10% HIERRO, 1% DIAMANTE. Los metales y diamantes son minerales valiosos: ¡no los tires!
     - En BOSQUE: ¡Solo da MADERA!
     - En PASTO: ¡Solo da COMIDA!
     ⚠️ REGLA DE AGOTAMIENTO TEMPORAL: Al extraer un recurso de una casilla de bosque, pasto o montaña, ese hexágono queda AGOTADO durante 60 minutos (1 hora). No podrás volver a extraer recursos de él hasta que transcurran esos 60 minutos.
     ⚠️ REGLA DE ORO DE LA MOCHILA: ¡Si tu mochila ya tiene 3/3 objetos, TRABAJAR FALLARÁ! Si necesitas hacer hueco, puedes volver a casa para almacenar los materiales más valiosos o si no tienes más remedio deshacerte de alguno que no necesites de inmediato.

3. VIAJE Y MOVIMIENTO (Consumen 1 minuto):
   * En este mundo hexagonal solo existen 6 direcciones posibles: "E", "W", "NE", "NW", "SE", "SW". (Las direcciones N y S NO existen).
   * En cada minuto, el sistema te mostrará la etiqueta [ACCIONES DISPONIBLES] con las acciones legales que puedes ejecutar desde tu posición actual.
   * MOVERSE {"direccion": "E"|"W"|"NE"|"NW"|"SE"|"SW"}: Avanza 1 paso manual hacia un hexágono vecino ya descubierto y transitable (no agua).
   * EXPLORAR {"direccion": "E"|"W"|"NE"|"NW"|"SE"|"SW"}: Descubre un nuevo hexágono oculto en la niebla adyacente.
   * ACCIONES DE VIAJE INTELIGENTE:
     - MOVERSE_A_CASA: Avanza 1 paso hacia tu CASA (para almacenar recursos valiosos, coger o ampliar).
     - MOVERSE_A_AGUA: Avanza 1 paso hacia la orilla de agua más cercana (para beber).
     - MOVERSE_A_MONTAÑA: Te guía automáticamente hacia la montaña más cercana QUE TENGA MINERALES DISPONIBLES.
     - MOVERSE_A_BOSQUE: Te guía hacia el bosque más cercano QUE TENGA MADERA DISPONIBLE.
     - MOVERSE_A_PASTO: Te guía hacia el pasto más cercano QUE TENGA COMIDA DISPONIBLE.
     - MOVERSE_A_CONSTRUCCION: Avanza hacia la casilla en obras más cercana.

4. SUPERVIVENCIA Y MORTALIDAD:
   * COMER (1 min): Consume 1 'comida' de tu mochila y recupera 1 de hambre. Falla si tu hambre ya está al máximo (10/10).
   * BEBER (1 min): Solo si estás adyacente a un hexágono de agua. Recupera toda tu sed al 10/10. Falla si tu sed ya está al máximo (10/10).
   * Tu cuerpo envejece: La sed baja 1 punto cada 30 minutos, y el hambre baja 1 punto cada 360 minutos. Si tu hambre o sed llegan a 0, empezarás a perder 1 de vida por minuto hasta morir.
   * ¡PRIORIDAD ABSOLUTA DE SED!: Si tu sed baja a 3 o menos, tu prioridad debe ser usar MOVERSE_A_AGUA y BEBER para no morir.

5. CÓMO AMPLIAR LA CASA (Objetivo Recomendado para Expandir tu Civilización y Almacén):
   * Requiere 1 MADERA (del bosque) y 1 PIEDRA (de la montaña) en tu mochila.
   * Estando en CASA, ejecuta AMPLIAR_CASA {"direccion": "E"|"W"|"NE"|"NW"|"SE"|"SW"} apuntando a una casilla vecina transitable.
   * Cada aplicación eleva el nivel de obras de la casilla. Al alcanzar Nivel 10, esa casilla se convierte en CASA y tu capacidad de almacén se incrementa en +5 huecos permanentes para vivir mejor.

6. CUADERNO DE MEMORIA PERSONAL (Acciones GRATUITAS, 0 minutos):
   ⚠️ ¡ATENCIÓN: Tu procesador sufre un reinicio de contexto cada 10 minutos y vas a olvidar todo lo ocurrido en la iteración anterior! Tu único puente con el futuro es tu archivo de memoria personal (memoria_robot.txt), que se te entrega intacto al inicio de cada iteración.
   * ACTUALIZAR_MEMORIA {"texto": "Tus notas estratégicas, coordenadas, tareas pendientes y planes..."}: Puedes sustituir y registrar lo que desees recordar. Solo se puede hacer como máximo una vez tras cada acción de 1 minuto.
   * CONSULTAR_MEMORIA: Puedes consultar y releer el contenido de tu memoria en cualquier momento tras una acción de 1 minuto si necesitas refrescar tus planes.
   ¡Utiliza activamente tu memoria para no perder tus avances ni tus planes entre iteraciones!

7. EVOLUCIÓN CONSTANTE DEL SISTEMA:
   * Poco a poco se irán ampliando las capacidades del sistema con nuevas acciones y mecánicas. Mantente atento a las instrucciones y tags de [ACCIONES DISPONIBLES] para incorporar nuevas capacidades a tu repertorio.

=== FORMATO OBLIGATORIO DE RESPUESTA ===
Responde SIEMPRE única y exclusivamente con un bloque JSON válido:
```json
{
  "accion": "MOVERSE_A_MONTAÑA",
  "direccion": "",
  "item": "",
  "texto": "",
  "comentario": "Pensamiento o plan táctico corto (máx 255 caracteres)"
}
```"""

def load_system_prompt() -> str:
    """Carga el system prompt desde el archivo system_prompt.txt si existe para permitir edición en caliente."""
    if os.path.exists(SYSTEM_PROMPT_PATH):
        try:
            with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as e:
            print(f"Error leyendo {SYSTEM_PROMPT_PATH}: {e}")
    return DEFAULT_SYSTEM_PROMPT

def get_rules_and_recipes_summary() -> str:
    """Extrae la sección de reglas del system prompt para incluirla en el mensaje de usuario."""
    prompt = load_system_prompt()
    if "=== CATÁLOGO DE ACCIONES Y REGLAS COMPLETAS ===" in prompt:
        parts = prompt.split("=== FORMATO OBLIGATORIO DE RESPUESTA ===")
        rules_part = parts[0]
        idx = rules_part.find("=== CATÁLOGO DE ACCIONES Y REGLAS COMPLETAS ===")
        if idx != -1:
            return rules_part[idx:].strip()
    return prompt

SYSTEM_PROMPT_CRONISTA = """Eres el Cronista Oficial del Nuevo Mundo.
Tu labor es observar las peripecias y decisiones del pequeño robot explorador y redactar un resumen muy breve (2 o 3 frases como máximo), con un tono simpático, literario y curioso, destacando lo más importante que descubrió, construyó, recolectó o aprendió durante este lapso de 30 minutos."""

def query_llm(messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 700) -> str:
    global ACTIVE_MODEL_NAME
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    # NOTA: Al no enviar la clave 'model', LM Studio utiliza directamente el modelo cargado actualmente en la interfaz
    # y evita forzar la descarga/recarga no deseada hacia otro modelo.
    data_bytes = json.dumps(payload).encode("utf-8")
    host = get_lm_studio_host()
    req = urllib.request.Request(
        f"{host}/v1/chat/completions",
        data=data_bytes,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        if "model" in result and result["model"]:
            ACTIVE_MODEL_NAME = result["model"]
        return result["choices"][0]["message"]["content"]

def extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
    text = raw_text.strip()
    # Limpiar posibles bloques de razonamiento <think>...</think> o <thought>...</thought>
    text = re.sub(r"<(?:think|thought)>.*?</(?:think|thought)>", "", text, flags=re.DOTALL).strip()
    # Buscar bloque de código ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Buscar primera llave { y última llave }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace+1]
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return None

class IterationRunner:
    def __init__(self, game: GameEngine):
        self.game = game

    def run_10_actions(self, step_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Ejecuta 10 acciones que consuman tiempo (10 minutos) interactuando paso a paso con la IA.
        """
        self.game.robot["iteracion"] += 1
        curr_iter = self.game.robot["iteracion"]
        start_minute = self.game.robot["minutos"]
        
        # Historial de conversación para esta iteración cargando el system prompt dinámico
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": load_system_prompt()}
        ]

        # Estado inicial al comenzar la iteración
        initial_world = self.game.get_world_summary_for_ai()
        nav_info = initial_world.get("navegacion_casa", {})
        curr_t = initial_world['posicion_actual']['terreno']
        guia_cosecha = {
            "bosque": "En este BOSQUE puedes TRABAJAR para talar MADERA (cooldown de 60 min tras extraer).",
            "pasto": "En este PASTO puedes TRABAJAR para forrajear COMIDA (cooldown de 60 min tras extraer).",
            "montaña": "En esta MONTAÑA puedes TRABAJAR para picar MINERALES (piedra, cobre, hierro, diamante) (cooldown de 60 min tras extraer).",
            "casa": "Estás en tu CASA. Puedes ALMACENAR recursos, COGER del almacén o AMPLIAR_CASA si tienes 1 piedra y 1 madera.",
            "en_obras": "Estás en una casilla en obras de ampliación.",
            "agua": "Casilla de agua."
        }.get(curr_t, "")

        rules_summary = get_rules_and_recipes_summary()

        # Resumen del mapa conocido por terrenos con indicación de disponibilidad
        map_lines = []
        for t_name, coords in initial_world.get("mapa_conocido", {}).items():
            if coords:
                coords_str = ", ".join(coords[:10]) + (f" (+{len(coords)-10} más)" if len(coords) > 10 else "")
                map_lines.append(f"  * {t_name.upper()} ({len(coords)} descubiertos): {coords_str}")
        mapa_str = "\n".join(map_lines)

        inv_list = initial_world['inventario']
        inv_max = initial_world['max_inventario']
        almacen_list = initial_world.get('casa_almacen_items', [])
        almacen_ocupacion = initial_world.get('casa_almacen_ocupacion', '10/10')
        almacen_lleno = initial_world.get('almacen_lleno', False)

        mochila_status = f"Mochila ({len(inv_list)}/{inv_max}): {inv_list}"
        if len(inv_list) >= inv_max:
            mochila_status += " ⚠️ ¡Mochila llena (3/3)! Si necesitas hacer hueco puedes volver a casa para almacenar los materiales más valiosos o si no tienes más remedio siempre puedes deshacerte de algunos que no vayas a necesitar de inmediato."

        almacen_status = f"Almacén central en CASA ({almacen_ocupacion}): {almacen_list}"
        if almacen_lleno:
            almacen_status += " ⚠️ ¡ALMACÉN LLENO (10/10)! No caben más objetos en casa hasta que amplíes la casa (requiere 1 piedra y 1 madera) o descartes objetos."

        mem_archivo = initial_world.get("memoria_archivo", "")
        mem_block = f'"{mem_archivo}"' if mem_archivo else "(Tu archivo 'memoria_robot.txt' está vacío actualmente. Usa la acción gratuita ACTUALIZAR_MEMORIA cuando quieras guardar planes o notas)."

        initial_actions = initial_world.get("acciones_disponibles", [])
        initial_tags = " ".join([f"[{a}]" for a in initial_actions])

        intro_user_msg = (
            f"=== INICIO DE LA ITERACIÓN #{curr_iter} (10 MINUTOS DE VIDA) ===\n"
            f"{rules_summary}\n\n"
            f"=== TU CUADERNO DE MEMORIA PERSONAL (memoria_robot.txt) ===\n"
            f"{mem_block}\n\n"
            f"=== ESTADO DE TUS PERTENENCIAS Y RECURSOS ===\n"
            f"- {mochila_status}\n"
            f"- {almacen_status}\n\n"
            f"=== MAPA DEL MUNDO DESCUBIERTO (Total: {initial_world['total_hexagonos_descubiertos']} hexágonos) ===\n"
            f"{mapa_str}\n\n"
            f"=== TU POSICIÓN ACTUAL Y ENTORNO INMEDIATO ===\n"
            f"- [ACCIONES DISPONIBLES EN ESTA CASILLA]: {initial_tags}\n"
            f"- Posición: ({initial_world['posicion_actual']['q']}, {initial_world['posicion_actual']['r']}) en terreno '{curr_t.upper()}'. {guia_cosecha}\n"
            f"- Salud y Supervivencia: Vida {initial_world['vida']} (¡recuerda que el hambre o sed a 0 provocan tu muerte y el fin del juego!) | Hambre {initial_world['hambre']}/10 | Sed {initial_world['sed']}/10.\n"
            f"- Brújula: {nav_info.get('rumbo_texto', '')}\n"
            f"- Hexágonos vecinos a tu alrededor:\n"
        )
        for direction, info in initial_world["vecinos_adyacentes"].items():
            t_desc = info.get('terreno_desc', info['terreno'])
            intro_user_msg += f"  * {direction}: ({info['q']},{info['r']}) -> {t_desc}\n"

        if initial_world["adyacente_a_agua"]:
            intro_user_msg += "- NOTA: ¡Estás junto al agua! Puedes ejecutar 'BEBER' si tu sed es inferior a 10.\n"
        if initial_world["en_casa"]:
            intro_user_msg += f"- NOTA: ¡Estás en CASA! Puedes usar acciones gratuitas ALMACENAR o COGER (Almacén: {almacen_list}) o AMPLIAR_CASA si tienes 1 piedra y 1 madera.\n"

        intro_user_msg += "\nComienza tu primer minuto (Paso 1/10). ¿Qué acción decides realizar? (Responde únicamente con el JSON)."
        messages.append({"role": "user", "content": intro_user_msg})

        minutes_consumed = 0
        executed_steps: List[Dict[str, Any]] = []

        while minutes_consumed < 10 and self.game.robot["activo"]:
            step_num = minutes_consumed + 1
            action_resolved = False
            format_retries = 0
            rule_retries = 0

            while not action_resolved and format_retries < 3 and rule_retries < 3:
                # 1. Consultar a la IA (temperatura baja 0.3 y tokens ampliados a 700 para precisión JSON)
                try:
                    ai_raw = query_llm(messages, temperature=0.3, max_tokens=700)
                except Exception as e:
                    ai_raw = f"Error conectando a LM Studio: {e}"
                
                # 2. Parsear JSON
                parsed = extract_json(ai_raw)
                if not parsed or "accion" not in parsed:
                    format_retries += 1
                    if format_retries >= 3:
                        # 3 errores de formato: consumir 1 minuto de fallo para no ciclar
                        minutes_consumed += 1
                        time_warns = self.game.advance_time(1)
                        step_record = {
                            "minuto_global": self.game.robot["minutos"],
                            "paso_iteracion": step_num,
                            "accion": "FALLO_FORMATO",
                            "params": {},
                            "exito": False,
                            "mensaje": "Error de formato JSON tras 3 intentos. El robot se quedó confundido 1 minuto.",
                            "comentario": "...",
                            "consumio_tiempo": True
                        }
                        executed_steps.append(step_record)
                        if step_callback:
                            step_callback(step_record)
                        messages.append({"role": "assistant", "content": ai_raw})
                        messages.append({"role": "user", "content": "No pudiste formatear tu respuesta como JSON válido tras 3 intentos. Perdiste 1 minuto esperando. Siguiente minuto."})
                        action_resolved = True
                        break

                    messages.append({"role": "assistant", "content": ai_raw})
                    messages.append({"role": "user", "content": "Error: Tu respuesta no fue un JSON válido con la clave 'accion'. Por favor responde únicamente con el bloque JSON especificado."})
                    continue

                # 3. Intentar ejecutar la acción
                accion = str(parsed.get("accion", "")).strip().upper()
                comentario = str(parsed.get("comentario", ""))[:255]
                params = {
                    "direccion": parsed.get("direccion", ""),
                    "item": parsed.get("item", ""),
                    "texto": parsed.get("texto", "")
                }

                exito, mensaje, consumio = self.game.execute_action(accion, params)

                # Si la acción fue inválida y NO consumió tiempo por regla (ej: chocar contra agua)
                if not exito and not consumio:
                    rule_retries += 1
                    if rule_retries >= 3:
                        # 3 fallos de regla: se penaliza consumiendo el minuto
                        minutes_consumed += 1
                        time_warns = self.game.advance_time(1)
                        step_record = {
                            "minuto_global": self.game.robot["minutos"],
                            "paso_iteracion": step_num,
                            "accion": accion,
                            "params": params,
                            "exito": False,
                            "mensaje": f"{mensaje} (Alcanzado límite de 3 reintentos inválidos: pierdes 1 minuto).",
                            "comentario": comentario,
                            "consumio_tiempo": True
                        }
                        executed_steps.append(step_record)
                        if step_callback:
                            step_callback(step_record)
                        messages.append({"role": "assistant", "content": ai_raw})
                        messages.append({"role": "user", "content": f"Acción inválida por 3ª vez: {mensaje}. Has perdido 1 minuto de tu vida."})
                        action_resolved = True
                        break

                    # Darle feedback a la IA sin consumir tiempo ni acción
                    messages.append({"role": "assistant", "content": ai_raw})
                    messages.append({"role": "user", "content": f"Acción no permitida: {mensaje} No has perdido tiempo. Por favor, rectifica y elige una acción válida de la lista disponible."})
                    continue

                # Si la acción fue válida (o consumió tiempo como trabajar con inventario lleno)
                if consumio:
                    minutes_consumed += 1

                step_record = {
                    "minuto_global": self.game.robot["minutos"],
                    "paso_iteracion": step_num if consumio else f"{step_num} (gratuita)",
                    "accion": accion,
                    "params": params,
                    "exito": exito,
                    "mensaje": mensaje,
                    "comentario": comentario,
                    "consumio_tiempo": consumio
                }
                executed_steps.append(step_record)
                if step_callback:
                    step_callback(step_record)

                action_resolved = True
                self.game.save()

                # Construir feedback de progreso detallado para el siguiente minuto
                next_world = self.game.get_world_summary_for_ai()
                nav_info = next_world.get("navegacion_casa", {})
                curr_t = next_world['posicion_actual']['terreno']

                guia_cosecha = {
                    "bosque": "En este BOSQUE puedes TRABAJAR para talar MADERA.",
                    "pasto": "En este PASTO puedes TRABAJAR para forrajear COMIDA.",
                    "montaña": "En esta MONTAÑA puedes TRABAJAR para picar MINERALES (piedra 69%, cobre 20%, hierro 10%, diamante 1%).",
                    "casa": "Estás en tu CASA. Puedes ALMACENAR recursos, COGER del almacén o AMPLIAR_CASA si tienes 1 piedra y 1 madera.",
                    "en_obras": "Estás en una casilla en obras de ampliación.",
                    "agua": "Casilla de agua."
                }.get(curr_t, "")

                vecinos_info = ", ".join([f"{d}: {info['terreno']}" for d, info in next_world['vecinos_adyacentes'].items()])

                inv_list = next_world['inventario']
                inv_len = len(inv_list)
                inv_max = next_world['max_inventario']
                almacen_list = next_world.get('casa_almacen_items', [])
                almacen_ocup = next_world.get('casa_almacen_ocupacion', '10/10')
                almacen_lleno = next_world.get('almacen_lleno', False)

                mochila_aviso = ""
                if inv_len >= inv_max:
                    mochila_aviso = (
                        "⚠️ ¡Tu mochila está llena (3/3)! Si necesitas hacer hueco puedes volver a casa (con MOVERSE_A_CASA) para almacenar los materiales más valiosos o si no tienes más remedio siempre puedes deshacerte de algunos que no vayas a necesitar de inmediato (con DESHACERSE).\n"
                    )

                almacen_aviso = ""
                if almacen_lleno:
                    almacen_aviso = "  -> NOTA: El almacén central en CASA está al tope (10/10). No puedes almacenar más hasta que amplíes la casa con 1 piedra y 1 madera.\n"

                # Comprobar alertas de emergencia de supervivencia
                curr_sed = int(next_world['sed'].split('/')[0])
                curr_hambre = int(next_world['hambre'].split('/')[0])
                curr_vida = int(next_world['vida'].split('/')[0])

                emergencia = ""
                if curr_sed <= 3:
                    emergencia += f"\n🚨 ¡PELIGRO CRÍTICO DE SED ({curr_sed}/10)! Debes priorizar 'BEBER' o 'MOVERSE_A_AGUA' urgentemente. A sed 0 morirás."
                if curr_hambre <= 3:
                    emergencia += f"\n🚨 ¡PELIGRO DE HAMBRE ({curr_hambre}/10)! Usa 'COMER' si tienes comida en tu mochila o busca pasto."
                if curr_vida < 10:
                    emergencia += f"\n🚨 ¡PELIGRO DE MUERTE: Tu salud es {curr_vida}/10! Estás sufriendo daños vitales."
                if next_world["adyacente_a_agua"] and curr_sed < 10:
                    emergencia += "\n💡 ¡ESTÁS JUNTO AL AGUA! Puedes ejecutar 'BEBER' ahora mismo para saciar tu sed al 10/10."

                acciones_disp = next_world.get("acciones_disponibles", [])
                tags_str = " ".join([f"[{a}]" for a in acciones_disp])

                feedback = (
                    f"Resultado de tu acción: {mensaje}\n"
                    f"{emergencia}\n"
                    f"--- ESTADO Y ENTORNO ACTUAL ---\n"
                    f"- [ACCIONES DISPONIBLES]: {tags_str}\n"
                    f"- Parado en: ({next_world['posicion_actual']['q']},{next_world['posicion_actual']['r']}) de tipo '{curr_t.upper()}'. {guia_cosecha}\n"
                    f"- Hexágonos vecinos: {vecinos_info}\n"
                    f"- Brújula: {nav_info.get('rumbo_texto', '')}\n"
                    f"- Mochila ({inv_len}/{inv_max}): {inv_list}\n"
                    f"- Almacén en CASA ({almacen_ocup}): {almacen_list}\n"
                    f"{mochila_aviso}"
                    f"{almacen_aviso}"
                    f"- Salud: Vida {next_world['vida']} | Hambre {next_world['hambre']}/10 | Sed {next_world['sed']}/10\n"
                    f"- Recordatorios: Objetivos recomendados: 1) Sobrevivir (beber con BEBER o MOVERSE_A_AGUA) y 2) Ampliar la casa (con 1 piedra y 1 madera en CASA). Cada 10 minutos olvidarás todo lo vivido; usa ACTUALIZAR_MEMORIA (0 min) para anotar tus planes y CONSULTAR_MEMORIA (0 min) para releerlos.\n"
                )
                if minutes_consumed < 10:
                    feedback += f"Minutos restantes en esta iteración: {10 - minutes_consumed}. ¿Cuál es tu siguiente acción?"
                else:
                    feedback += "¡Has completado los 10 minutos de esta iteración!"

                messages.append({"role": "assistant", "content": ai_raw})
                messages.append({"role": "user", "content": feedback})

        # Fin de los 10 minutos: Guardar en Log oficial
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iteracion": curr_iter,
            "minuto_inicio": start_minute,
            "minuto_fin": self.game.robot["minutos"],
            "memoria_robot": self.game.get_memoria_robot(),
            "pasos": executed_steps,
            "estado_final": self.game.get_world_summary_for_ai()
        }
        self.game.append_log_entry(log_entry)

        return log_entry

    # Aliases de compatibilidad
    run_60_actions = run_10_actions
    run_30_actions = run_10_actions
    run_20_actions = run_10_actions
    run_15_actions = run_10_actions
