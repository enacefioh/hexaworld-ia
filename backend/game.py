import json
import os
import random
from typing import Dict, Any, List, Optional, Tuple

DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "E": (1, 0),
    "W": (-1, 0),
    "NE": (1, -1),
    "NW": (0, -1),
    "SE": (0, 1),
    "SW": (-1, 1),
}

OPPOSITE_DIRECTIONS = {
    "E": "W", "W": "E",
    "NE": "SW", "SW": "NE",
    "NW": "SE", "SE": "NW"
}

SAVE_FILE = os.path.join(os.path.dirname(__file__), "game_state.json")
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "game_log.json")
TXT_LOG_FILE = os.path.join(LOG_DIR, "game_log.txt")
MEMORIA_ROBOT_FILE = os.path.join(os.path.dirname(__file__), "..", "memoria_robot.txt")

os.makedirs(LOG_DIR, exist_ok=True)

class GameEngine:
    def __init__(self):
        if os.path.exists(SAVE_FILE):
            try:
                self.load()
            except Exception as e:
                print(f"Error cargando partida previa: {e}. Iniciando nueva.")
                self.reset()
        else:
            self.reset()

    def reset(self):
        self.hexes: Dict[str, Dict[str, Any]] = {
            "0,0": {
                "q": 0,
                "r": 0,
                "discovered": True,
                "terrain": "casa",
                "agotado_hasta_minuto": 0
            }
        }
        self.robot = {
            "q": 0,
            "r": 0,
            "vida": 10,
            "max_vida": 10,
            "hambre": 5,
            "max_hambre": 10,
            "sed": 5,
            "max_sed": 10,
            "inventario": [],
            "max_inventario": 3,
            "casa_almacen": [],
            "max_casa_almacen": 10,
            "minutos": 0,
            "iteracion": 0,
            "activo": True,
            "memoria_actualizada_este_turno": False,
            "memoria_consultada_este_turno": False
        }
        self.history: List[Dict[str, Any]] = []
        self.set_memoria_robot("")
        self.save()

    def get_memoria_robot(self) -> str:
        if os.path.exists(MEMORIA_ROBOT_FILE):
            try:
                with open(MEMORIA_ROBOT_FILE, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Error leyendo {MEMORIA_ROBOT_FILE}: {e}")
        return ""

    def set_memoria_robot(self, texto: str):
        try:
            with open(MEMORIA_ROBOT_FILE, "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            print(f"Error escribiendo {MEMORIA_ROBOT_FILE}: {e}")

    def save(self):
        data = {
            "hexes": self.hexes,
            "robot": self.robot,
            "history": self.history[-50:] # guardamos los últimos 50 eventos
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.hexes = data.get("hexes", {})
            self.robot = data.get("robot", {})
            self.history = data.get("history", [])
            self.robot.setdefault("max_casa_almacen", 10)
            self.robot.setdefault("max_inventario", 3)
            self.robot.setdefault("memoria_actualizada_este_turno", False)
            self.robot.setdefault("memoria_consultada_este_turno", False)

    def get_hex(self, q: int, r: int) -> Optional[Dict[str, Any]]:
        return self.hexes.get(f"{q},{r}")

    def is_at_home(self, q: int, r: int) -> bool:
        h = self.get_hex(q, r)
        return bool(h and h.get("terrain") == "casa")

    def get_adjacent_info(self, q: int, r: int) -> Dict[str, Dict[str, Any]]:
        adjacent = {}
        curr_min = self.robot["minutos"]
        for dir_name, (dq, dr) in DIRECTIONS.items():
            nq, nr = q + dq, r + dr
            key = f"{nq},{nr}"
            if key in self.hexes and self.hexes[key]["discovered"]:
                hex_data = self.hexes[key]
                t = hex_data["terrain"]
                t_desc = t
                agotado_hasta = hex_data.get("agotado_hasta_minuto", 0)
                if t in ("bosque", "pasto", "montaña"):
                    if agotado_hasta > curr_min:
                        t_desc += f" [Agotado: faltan {agotado_hasta - curr_min}m]"
                    else:
                        t_desc += " [Disponible]"
                adjacent[dir_name] = {
                    "q": nq,
                    "r": nr,
                    "descubierto": True,
                    "terreno": t,
                    "terreno_desc": t_desc,
                    "agotado_hasta_minuto": agotado_hasta
                }
            else:
                adjacent[dir_name] = {
                    "q": nq,
                    "r": nr,
                    "descubierto": False,
                    "terreno": "desconocido (niebla)",
                    "terreno_desc": "desconocido (niebla)",
                    "agotado_hasta_minuto": 0
                }
        return adjacent

    def is_adjacent_to_water(self, q: int, r: int) -> bool:
        for dq, dr in DIRECTIONS.values():
            key = f"{q + dq},{r + dr}"
            if key in self.hexes and self.hexes[key].get("discovered") and self.hexes[key].get("terrain") == "agua":
                return True
        return False

    def get_navigation_to_home(self, q: int, r: int) -> Dict[str, Any]:
        casa_hexes = [h for h in self.hexes.values() if h.get("terrain") == "casa"]
        if not casa_hexes:
            return {"en_casa": True, "distancia_pasos": 0, "direccion_recomendada": None, "rumbo_texto": "Estás en casa."}

        closest_casa = None
        min_dist = 999999
        for ch in casa_hexes:
            d = (abs(q - ch["q"]) + abs(r - ch["r"]) + abs((-q - r) - (-ch["q"] - ch["r"]))) // 2
            if d < min_dist:
                min_dist = d
                closest_casa = ch

        if min_dist == 0:
            return {
                "en_casa": True,
                "distancia_pasos": 0,
                "direccion_recomendada": None,
                "rumbo_texto": "¡Estás en tu CASA! Puedes usar ALMACENAR, COGER o AMPLIAR_CASA."
            }

        cq, cr = closest_casa["q"], closest_casa["r"]
        best_dir = None
        valid_candidates = []
        all_candidates = []

        for dname, (dq, dr) in DIRECTIONS.items():
            nq, nr = q + dq, r + dr
            nd = (abs(nq - cq) + abs(nr - cr) + abs((-nq - nr) - (-cq - cr))) // 2
            if nd < min_dist:
                key = f"{nq},{nr}"
                is_safe = (key in self.hexes and self.hexes[key].get("discovered") and self.hexes[key].get("terrain") != "agua")
                if is_safe:
                    valid_candidates.append((nd, dname))
                all_candidates.append((nd, dname))

        if valid_candidates:
            valid_candidates.sort()
            best_dir = valid_candidates[0][1]
        elif all_candidates:
            all_candidates.sort()
            best_dir = all_candidates[0][1]

        return {
            "en_casa": False,
            "distancia_pasos": min_dist,
            "direccion_recomendada": best_dir,
            "casa_coordenadas": f"({cq},{cr})",
            "rumbo_texto": f"Tu CASA ({cq},{cr}) está a {min_dist} pasos de distancia. Rumbo recomendado para regresar: dirección {best_dir}."
        }

    def find_step_towards_terrain(self, target_type: str) -> Tuple[bool, str, Optional[str]]:
        rq, rr = self.robot["q"], self.robot["r"]
        target_type = target_type.lower().strip()
        curr_min = self.robot["minutos"]
        harvestable_terrains = ("bosque", "pasto", "montaña")
        all_matches = []
        targets = []

        for h in self.hexes.values():
            if not h.get("discovered"):
                continue
            if target_type in ("agua", "rio", "lago"):
                # Para agua: casillas transitables adyacentes al agua
                if h.get("terrain") != "agua" and self.is_adjacent_to_water(h["q"], h["r"]):
                    targets.append(h)
            elif target_type in ("casa", "hogar", "base"):
                if h.get("terrain") == "casa":
                    targets.append(h)
            elif target_type in ("construccion", "construcción", "en_obras", "obras"):
                if h.get("terrain") == "en_obras":
                    targets.append(h)
            elif target_type in harvestable_terrains:
                if h.get("terrain") == target_type:
                    all_matches.append(h)
                    # Solo considerar disponible si no está agotado
                    if h.get("agotado_hasta_minuto", 0) <= curr_min:
                        targets.append(h)
            else:
                if h.get("terrain") == target_type:
                    targets.append(h)

        if not targets:
            nombre = "en obras" if "obra" in target_type or "construc" in target_type else target_type
            if target_type in harvestable_terrains and all_matches:
                # Todos los hexágonos conocidos están en recarga
                soonest = min(all_matches, key=lambda x: x.get("agotado_hasta_minuto", 0))
                mins_left = max(1, soonest.get("agotado_hasta_minuto", 0) - curr_min)
                return False, f"Todos los hexágonos de tipo '{nombre}' conocidos están agotados temporalmente. El más próximo ({soonest['q']},{soonest['r']}) volverá a tener recursos en {mins_left} minutos. Debes esperar o EXPLORAR nuevos hexágonos.", None
            return False, f"Aún no hay ningún hexágono de tipo '{nombre}' descubierto en el mapa. Primero debes EXPLORAR más niebla.", None

        def dist_to_robot(th):
            tq, tr = th["q"], th["r"]
            return (abs(rq - tq) + abs(rr - tr) + abs((-rq - rr) - (-tq - tr))) // 2

        targets.sort(key=dist_to_robot)
        closest = targets[0]
        cdist = dist_to_robot(closest)

        if cdist == 0:
            if target_type in ("agua", "rio", "lago"):
                return False, f"Ya estás en ({rq},{rr}) junto al agua. Puedes usar BEBER directamente si tu sed es < 10.", None
            if target_type in harvestable_terrains:
                return False, f"Ya estás en ({rq},{rr}) de tipo '{target_type}' y TIENE RECURSOS DISPONIBLES. Puedes TRABAJAR aquí.", None
            return False, f"Ya estás ubicado en un hexágono de tipo '{target_type}' ({rq},{rr}).", None

        # Buscar el paso que más reduzca la distancia al objetivo más cercano
        candidates = []
        for dname, (dq, dr) in DIRECTIONS.items():
            nq, nr = rq + dq, rr + dr
            key = f"{nq},{nr}"
            if key in self.hexes and self.hexes[key].get("discovered") and self.hexes[key].get("terrain") != "agua":
                nd = (abs(nq - closest["q"]) + abs(nr - closest["r"]) + abs((-nq - nr) - (-closest["q"] - closest["r"]))) // 2
                if nd < cdist:
                    candidates.append((nd, dname))

        if candidates:
            candidates.sort()
            best_dir = candidates[0][1]
            return True, f"Rumbo hacia {target_type} ({closest['q']},{closest['r']}) a {cdist} pasos. Avanzando al {best_dir}.", best_dir

        # Si el camino directo está bloqueado, buscar cualquier paso transitable
        for dname, (dq, dr) in DIRECTIONS.items():
            nq, nr = rq + dq, rr + dr
            key = f"{nq},{nr}"
            if key in self.hexes and self.hexes[key].get("discovered") and self.hexes[key].get("terrain") != "agua":
                nd = (abs(nq - closest["q"]) + abs(nr - closest["r"]) + abs((-nq - nr) - (-closest["q"] - closest["r"]))) // 2
                candidates.append((nd, dname))

        if candidates:
            candidates.sort()
            best_dir = candidates[0][1]
            return True, f"Rodeando obstáculo hacia {target_type} ({closest['q']},{closest['r']}). Avanzando al {best_dir}.", best_dir

        return False, f"No hay camino transitable despejado hacia el objetivo de tipo '{target_type}'.", None

    def advance_time(self, minutes: int = 1) -> List[str]:
        warnings = []
        for _ in range(minutes):
            self.robot["minutos"] += 1
            curr_min = self.robot["minutos"]

            # Cada 30 minutos baja 1 de sed
            if curr_min % 30 == 0:
                self.robot["sed"] = max(0, self.robot["sed"] - 1)
                warnings.append(f"Ha pasado el tiempo: la sed bajó a {self.robot['sed']}/10.")

            # Cada 6 horas (360 minutos) baja 1 de hambre
            if curr_min % 360 == 0:
                self.robot["hambre"] = max(0, self.robot["hambre"] - 1)
                warnings.append(f"Han pasado 6 horas: el hambre bajó a {self.robot['hambre']}/10.")

            # Penalización si llega a 0
            if self.robot["sed"] == 0:
                self.robot["vida"] = max(0, self.robot["vida"] - 1)
                warnings.append(f"¡Alerta! Tienes 0 de sed. Pierdes 1 de vida. Vida actual: {self.robot['vida']}/10.")
            if self.robot["hambre"] == 0:
                self.robot["vida"] = max(0, self.robot["vida"] - 1)
                warnings.append(f"¡Alerta! Tienes 0 de hambre. Pierdes 1 de vida. Vida actual: {self.robot['vida']}/10.")

            if self.robot["vida"] <= 0:
                self.robot["activo"] = False
                warnings.append("¡Tu robot se ha apagado por falta de energía vital! (Game Over)")
                break

        return warnings

    def execute_action(self, action_type: str, params: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """
        Ejecuta una acción y gestiona el refresco de las acciones gratuitas de memoria.
        """
        exito, msg, consumio = self._execute_action_core(action_type, params)
        if consumio:
            self.robot["memoria_actualizada_este_turno"] = False
            self.robot["memoria_consultada_este_turno"] = False
        return exito, msg, consumio

    def _execute_action_core(self, action_type: str, params: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """
        Lógica interna de ejecución de acciones.
        Retorna:
          - exito: bool (si la acción fue válida o si falló por regla)
          - mensaje: str (explicación de lo sucedido)
          - consume_tiempo: bool (si consume 1 minuto)
        """
        if not self.robot["activo"]:
            return False, "El robot está desactivado.", False

        action_type = action_type.upper().strip()
        rq, rr = self.robot["q"], self.robot["r"]
        curr_hex = self.get_hex(rq, rr)

        # 1. EXPLORAR
        if action_type == "EXPLORAR":
            direction = str(params.get("direccion", "")).upper().strip()
            if direction not in DIRECTIONS:
                return False, f"Dirección '{direction}' no válida. Opciones: {list(DIRECTIONS.keys())}", False

            dq, dr = DIRECTIONS[direction]
            nq, nr = rq + dq, rr + dr
            key = f"{nq},{nr}"

            if key in self.hexes and self.hexes[key]["discovered"]:
                return False, f"El hexágono hacia el {direction} ({nq},{nr}) ya está descubierto ({self.hexes[key]['terrain']}).", False

            # Generar terreno aleatorio: pasto (35%), bosque (30%), montaña (20%), agua (15%)
            # Si es adyacente a agua ya descubierta, el agua tiene el doble de probabilidad (30%)
            adj_water = self.is_adjacent_to_water(nq, nr)
            water_weight = 30 if adj_water else 15
            terrain = random.choices(
                ["pasto", "bosque", "montaña", "agua"],
                weights=[35, 30, 20, water_weight]
            )[0]
            self.hexes[key] = {
                "q": nq,
                "r": nr,
                "discovered": True,
                "terrain": terrain
            }
            time_warnings = self.advance_time(1)
            warn_str = " " + " ".join(time_warnings) if time_warnings else ""
            return True, f"Has explorado hacia el {direction} y has descubierto un hexágono de tipo '{terrain}'.{warn_str}", True

        # 2. MOVERSE
        elif action_type == "MOVERSE":
            direction = str(params.get("direccion", "")).upper().strip()
            if direction not in DIRECTIONS:
                return False, f"Dirección '{direction}' no válida. Opciones: {list(DIRECTIONS.keys())}", False

            dq, dr = DIRECTIONS[direction]
            nq, nr = rq + dq, rr + dr
            key = f"{nq},{nr}"

            if key not in self.hexes or not self.hexes[key]["discovered"]:
                return False, f"El hexágono hacia el {direction} aún no ha sido explorado. Debes explorarlo antes de moverte a él.", False

            target_terrain = self.hexes[key]["terrain"]
            if target_terrain == "agua":
                return False, f"No puedes moverte hacia el {direction} porque es agua intransitable.", False

            self.robot["q"] = nq
            self.robot["r"] = nr
            time_warnings = self.advance_time(1)
            warn_str = " " + " ".join(time_warnings) if time_warnings else ""
            return True, f"Te has movido hacia el {direction} al hexágono ({nq},{nr}) de tipo '{target_terrain}'.{warn_str}", True

        # 3. TRABAJAR
        elif action_type == "TRABAJAR":
            # Si el inventario está lleno, la acción se procesa pero falla recolectar y pierde el minuto según la regla
            if len(self.robot["inventario"]) >= self.robot["max_inventario"]:
                time_warnings = self.advance_time(1)
                warn_str = " " + " ".join(time_warnings) if time_warnings else ""
                return False, f"Acción fallida: Tu inventario está lleno ({len(self.robot['inventario'])}/{self.robot['max_inventario']}). No has recolectado nada y has perdido 1 minuto.{warn_str}", True

            terrain = curr_hex["terrain"] if curr_hex else ""
            if terrain not in ("bosque", "pasto", "montaña"):
                return False, f"No puedes trabajar en el terreno actual ({terrain}). Solo puedes trabajar en bosque (madera), pasto (comida) o montaña (minerales).", False

            curr_min = self.robot["minutos"]
            agotado_hasta = curr_hex.get("agotado_hasta_minuto", 0)
            if curr_min < agotado_hasta:
                restante = max(1, agotado_hasta - curr_min)
                return False, f"El terreno ({rq},{rr}) de tipo '{terrain}' está agotado temporalmente. Se regenerará en {restante} minutos. Debes moverte a otro hexágono o explorar.", False

            if terrain == "bosque":
                self.robot["inventario"].append("madera")
                curr_hex["agotado_hasta_minuto"] = curr_min + 60
                time_warnings = self.advance_time(1)
                warn_str = " " + " ".join(time_warnings) if time_warnings else ""
                return True, f"Has trabajado talando en el bosque y conseguiste 1 madera. Este bosque queda agotado durante 60 minutos. Inventario: {self.robot['inventario']}.{warn_str}", True
            elif terrain == "pasto":
                self.robot["inventario"].append("comida")
                curr_hex["agotado_hasta_minuto"] = curr_min + 60
                time_warnings = self.advance_time(1)
                warn_str = " " + " ".join(time_warnings) if time_warnings else ""
                return True, f"Has trabajado forrajeando en el pasto y conseguiste 1 comida. Este pasto queda agotado durante 60 minutos. Inventario: {self.robot['inventario']}.{warn_str}", True
            elif terrain == "montaña":
                # 1% diamante, 10% hierro, 20% cobre, 69% piedra
                mineral = random.choices(["diamante", "hierro", "cobre", "piedra"], weights=[1, 10, 20, 69])[0]
                self.robot["inventario"].append(mineral)
                curr_hex["agotado_hasta_minuto"] = curr_min + 60
                time_warnings = self.advance_time(1)
                warn_str = " " + " ".join(time_warnings) if time_warnings else ""
                return True, f"Has trabajado picando en la montaña y conseguiste 1 {mineral}. Esta montaña queda agotada durante 60 minutos. Inventario: {self.robot['inventario']}.{warn_str}", True

        # 4. COMER
        elif action_type == "COMER":
            if self.robot["hambre"] >= self.robot["max_hambre"]:
                return False, f"Tu nivel de hambre ya está al máximo ({self.robot['hambre']}/{self.robot['max_hambre']}). No necesitas comer ahora.", False

            if "comida" not in self.robot["inventario"]:
                return False, "No tienes ningún ítem de comida en tu inventario para comer.", False

            self.robot["inventario"].remove("comida")
            self.robot["hambre"] = min(self.robot["max_hambre"], self.robot["hambre"] + 1)
            time_warnings = self.advance_time(1)
            warn_str = " " + " ".join(time_warnings) if time_warnings else ""
            return True, f"Has comido 1 ración de comida. Tu nivel de hambre ahora es {self.robot['hambre']}/10.{warn_str}", True

        # 5. BEBER
        elif action_type == "BEBER":
            if self.robot["sed"] >= self.robot["max_sed"]:
                return False, f"Tu nivel de sed ya está al máximo ({self.robot['sed']}/{self.robot['max_sed']}). No necesitas beber ahora.", False

            if not self.is_adjacent_to_water(rq, rr):
                return False, "No estás adyacente a ningún hexágono de agua para beber.", False

            self.robot["sed"] = self.robot["max_sed"]
            time_warnings = self.advance_time(1)
            warn_str = " " + " ".join(time_warnings) if time_warnings else ""
            return True, f"Has bebido agua fresca de la orilla adyacente. Tu sed se ha recuperado por completo (10/10).{warn_str}", True

        # 6. ALMACENAR (Acción gratuita, 0 minutos)
        elif action_type == "ALMACENAR":
            if not self.is_at_home(rq, rr):
                return False, "Solo puedes almacenar objetos si estás en tu casa.", False

            if not self.robot["inventario"]:
                return False, "Tu inventario está vacío, no tienes objetos para almacenar.", False

            item_str = str(params.get("item", "")).strip().lower()
            almacenados = []

            # Si no se especifica item o se dice 'todo' / 'all', guardar todo lo posible
            if not item_str or item_str in ("todo", "todos", "all"):
                while self.robot["inventario"] and len(self.robot["casa_almacen"]) < self.robot["max_casa_almacen"]:
                    it = self.robot["inventario"].pop(0)
                    self.robot["casa_almacen"].append(it)
                    almacenados.append(it)
                if not almacenados and len(self.robot["casa_almacen"]) >= self.robot["max_casa_almacen"]:
                    return False, f"El almacén de la casa está lleno ({self.robot['max_casa_almacen']}/{self.robot['max_casa_almacen']} objetos).", False
            else:
                target_item = item_str
                if target_item in self.robot["inventario"]:
                    if len(self.robot["casa_almacen"]) < self.robot["max_casa_almacen"]:
                        self.robot["inventario"].remove(target_item)
                        self.robot["casa_almacen"].append(target_item)
                        almacenados.append(target_item)
                    else:
                        return False, f"El almacén de la casa está lleno ({self.robot['max_casa_almacen']}/{self.robot['max_casa_almacen']} objetos).", False
                else:
                    return False, f"No tienes el ítem '{params.get('item')}' en tu inventario para almacenar. Tienes: {self.robot['inventario']}.", False

            return True, f"Has guardado en tu almacén: {almacenados}. Almacén actual ({len(self.robot['casa_almacen'])}/{self.robot['max_casa_almacen']}): {self.robot['casa_almacen']}. (Acción gratuita)", False

        # 7. COGER (Acción gratuita, 0 minutos)
        elif action_type == "COGER":
            if not self.is_at_home(rq, rr):
                return False, "Solo puedes coger objetos de tu almacén si estás en tu casa.", False

            if not self.robot["casa_almacen"]:
                return False, "El almacén de tu casa está vacío.", False

            if len(self.robot["inventario"]) >= self.robot["max_inventario"]:
                return False, f"Tu inventario ya está al máximo ({self.robot['max_inventario']} objetos).", False

            target_item = str(params.get("item", "")).lower()
            if target_item and target_item in self.robot["casa_almacen"]:
                self.robot["casa_almacen"].remove(target_item)
                self.robot["inventario"].append(target_item)
                cogido = target_item
            elif not target_item:
                cogido = self.robot["casa_almacen"].pop(0)
                self.robot["inventario"].append(cogido)
            else:
                return False, f"El ítem '{target_item}' no está disponible en el almacén de casa.", False

            return True, f"Has cogido '{cogido}' del almacén. Inventario: {self.robot['inventario']}. (Acción gratuita)", False

        # 8. DESHACERSE (Acción gratuita, 0 minutos)
        elif action_type == "DESHACERSE":
            target_item = str(params.get("item", "")).lower().strip()
            if not self.robot["inventario"]:
                return False, "Tu inventario ya está vacío, no tienes nada de lo que deshacerte.", False

            if not target_item:
                target_item = self.robot["inventario"][0]

            if target_item in ("todo", "todos", "all"):
                desechados = list(self.robot["inventario"])
                self.robot["inventario"].clear()
                return True, f"Te has deshecho de todos tus objetos: {desechados}. Mochila vacía (0/{self.robot['max_inventario']}). (Acción gratuita)", False

            if target_item in self.robot["inventario"]:
                self.robot["inventario"].remove(target_item)
                return True, f"Te has deshecho de '{target_item}'. Espacio liberado en inventario ({len(self.robot['inventario'])}/{self.robot['max_inventario']}). (Acción gratuita)", False
            else:
                return False, f"No tienes '{target_item}' en tu inventario para desecharlo. Tienes: {self.robot['inventario']}.", False

        # 9. AMPLIAR_CASA (Consume 1 minuto)
        elif action_type in ("AMPLIAR_CASA", "AMPLIAR"):
            if not self.is_at_home(rq, rr):
                return False, "Solo puedes ampliar la casa si estás actualmente en un hexágono de CASA.", False

            direction = str(params.get("direccion", "")).upper().strip()
            if direction not in DIRECTIONS:
                return False, f"Dirección '{direction}' no válida para ampliar. Opciones: {list(DIRECTIONS.keys())}", False

            dq, dr = DIRECTIONS[direction]
            nq, nr = rq + dq, rr + dr
            key = f"{nq},{nr}"

            if key not in self.hexes or not self.hexes[key].get("discovered"):
                return False, f"El hexágono hacia el {direction} ({nq},{nr}) debe estar explorado antes de ampliar la casa sobre él.", False

            target_hex = self.hexes[key]
            if target_hex.get("terrain") == "casa":
                return False, f"El hexágono hacia el {direction} ({nq},{nr}) ya es parte de tu CASA.", False

            # Verificar si tiene 1 piedra y 1 madera en inventario
            inv = self.robot["inventario"]
            if "piedra" not in inv or "madera" not in inv:
                return False, f"Para ampliar la casa necesitas 1 piedra y 1 madera en tu inventario. Tienes: {inv}.", False

            # Consumir materiales
            inv.remove("piedra")
            inv.remove("madera")

            time_warnings = self.advance_time(1)
            warn_str = " " + " ".join(time_warnings) if time_warnings else ""

            if target_hex.get("terrain") != "en_obras":
                target_hex["terrain"] = "en_obras"
                target_hex["nivel_obras"] = 1
                return True, f"Has iniciado las obras de ampliación hacia el {direction} en ({nq},{nr}) (Nivel 1/10). Gastaste 1 piedra y 1 madera.{warn_str}", True
            else:
                current_lvl = target_hex.get("nivel_obras", 1) + 1
                if current_lvl >= 10:
                    target_hex["terrain"] = "casa"
                    target_hex.pop("nivel_obras", None)
                    self.robot["max_casa_almacen"] += 5
                    return True, f"¡Obras completadas hacia el {direction}! El hexágono ({nq},{nr}) ahora es CASA. Tu almacén gana +5 casillas (capacidad total: {self.robot['max_casa_almacen']}). Gastaste 1 piedra y 1 madera.{warn_str}", True
                else:
                    target_hex["nivel_obras"] = current_lvl
                    return True, f"Has avanzado las obras de ampliación hacia el {direction} en ({nq},{nr}) a Nivel {current_lvl}/10. Gastaste 1 piedra y 1 madera.{warn_str}", True

        # 10. ACCIONES DE MOVIMIENTO AUTOMÁTICO A TERRENOS CERCANOS
        elif action_type in ("MOVERSE_A_MONTAÑA", "MOVERSE_A_BOSQUE", "MOVERSE_A_PASTO", "MOVERSE_A_AGUA", "MOVERSE_A_CASA", "MOVERSE_A_CONSTRUCCION", "MOVERSE_A_OBRAS",
                             "IR_A_MONTAÑA", "IR_A_BOSQUE", "IR_A_PASTO", "IR_A_AGUA", "IR_A_CASA", "IR_A_CONSTRUCCION", "IR_A_OBRAS"):
            terrain_map = {
                "MOVERSE_A_MONTAÑA": "montaña", "IR_A_MONTAÑA": "montaña",
                "MOVERSE_A_BOSQUE": "bosque", "IR_A_BOSQUE": "bosque",
                "MOVERSE_A_PASTO": "pasto", "IR_A_PASTO": "pasto",
                "MOVERSE_A_AGUA": "agua", "IR_A_AGUA": "agua",
                "MOVERSE_A_CASA": "casa", "IR_A_CASA": "casa",
                "MOVERSE_A_CONSTRUCCION": "en_obras", "IR_A_CONSTRUCCION": "en_obras",
                "MOVERSE_A_OBRAS": "en_obras", "IR_A_OBRAS": "en_obras"
            }
            ttype = terrain_map.get(action_type, "casa")
            ok, msg, move_dir = self.find_step_towards_terrain(ttype)
            if not ok or not move_dir:
                return False, msg, False

            exito, mov_msg, consumio = self.execute_action("MOVERSE", {"direccion": move_dir})
            return exito, f"{msg} -> {mov_msg}", consumio

        # 11. ACTUALIZAR_MEMORIA (Acción gratuita, 0 minutos, máximo 1 vez tras cada acción de 1 min)
        elif action_type in ("ACTUALIZAR_MEMORIA", "MODIFICAR_MEMORIA", "ESCRIBIR_MEMORIA", "GUARDAR_MEMORIA"):
            if self.robot.get("memoria_actualizada_este_turno", False):
                return False, "Ya has actualizado tu memoria tras tu última acción. Debes realizar una acción de 1 minuto antes de volver a modificarla.", False

            new_text = str(params.get("texto") or params.get("contenido") or params.get("item") or "").strip()
            if not new_text:
                return False, "Debes proporcionar el texto que deseas guardar en tu memoria en el campo 'texto'.", False

            self.set_memoria_robot(new_text)
            self.robot["memoria_actualizada_este_turno"] = True
            return True, "Has actualizado el archivo de tu memoria personal con éxito. (Acción gratuita)", False

        # 12. CONSULTAR_MEMORIA (Acción gratuita, 0 minutos, máximo 1 vez tras cada acción de 1 min)
        elif action_type in ("CONSULTAR_MEMORIA", "LEER_MEMORIA", "VER_MEMORIA"):
            if self.robot.get("memoria_consultada_este_turno", False):
                return False, "Ya has consultado tu memoria tras tu última acción. Debes realizar una acción de 1 minuto antes de volver a consultarla.", False

            self.robot["memoria_consultada_este_turno"] = True
            mem = self.get_memoria_robot()
            if not mem:
                return True, "Tu memoria personal (memoria_robot.txt) está actualmente vacía. Usa ACTUALIZAR_MEMORIA para guardar notas. (Acción gratuita)", False
            return True, f"Contenido actual de tu memoria personal: \"{mem}\". (Acción gratuita)", False

        else:
            return False, f"Acción desconocida '{action_type}'. Acciones permitidas: EXPLORAR, MOVERSE, TRABAJAR, COMER, BEBER, ALMACENAR, COGER, DESHACERSE, AMPLIAR_CASA, ACTUALIZAR_MEMORIA, CONSULTAR_MEMORIA, MOVERSE_A_MONTAÑA, MOVERSE_A_BOSQUE, MOVERSE_A_PASTO, MOVERSE_A_AGUA, MOVERSE_A_CASA, MOVERSE_A_CONSTRUCCION.", False

    def get_available_actions(self) -> List[str]:
        """
        Retorna la lista de tags de acciones que son válidas y posibles en el turno actual,
        considerando la posición del robot, sus hexágonos adyacentes y el estado global.
        """
        if not self.robot["activo"]:
            return []

        actions = []
        rq, rr = self.robot["q"], self.robot["r"]
        curr_hex = self.get_hex(rq, rr)
        curr_t = curr_hex["terrain"] if curr_hex else "desconocido"
        curr_min = self.robot["minutos"]
        inv = self.robot["inventario"]
        inv_len = len(inv)
        max_inv = self.robot["max_inventario"]
        almacen = self.robot["casa_almacen"]
        max_almacen = self.robot["max_casa_almacen"]
        at_home = self.is_at_home(rq, rr)
        adjacent = self.get_adjacent_info(rq, rr)

        # 1. Movimiento y Exploración local
        has_fog_neighbor = any(not info["descubierto"] for info in adjacent.values())
        if has_fog_neighbor:
            actions.append("EXPLORAR")

        has_walkable_neighbor = any(info["descubierto"] and info["terreno"] != "agua" for info in adjacent.values())
        if has_walkable_neighbor:
            actions.append("MOVERSE")

        # 2. Trabajo y recolección en casilla actual
        if curr_t in ("bosque", "pasto", "montaña"):
            agotado_hasta = curr_hex.get("agotado_hasta_minuto", 0) if curr_hex else 0
            if curr_min >= agotado_hasta and inv_len < max_inv:
                actions.append("TRABAJAR")

        # 3. Supervivencia
        if "comida" in inv and self.robot["hambre"] < self.robot["max_hambre"]:
            actions.append("COMER")

        if self.is_adjacent_to_water(rq, rr) and self.robot["sed"] < self.robot["max_sed"]:
            actions.append("BEBER")

        # 4. Gestión de Casa y Construcción
        if at_home:
            if inv_len > 0 and len(almacen) < max_almacen:
                actions.append("ALMACENAR")
            if len(almacen) > 0 and inv_len < max_inv:
                actions.append("COGER")
            if "piedra" in inv and "madera" in inv:
                actions.append("AMPLIAR_CASA")

        # 5. Gestión de Mochila (gratuita)
        if inv_len > 0:
            actions.append("DESHACERSE")

        # 6. Memoria Personal (gratuitas, máximo 1 vez tras acción de 1 min)
        if not self.robot.get("memoria_actualizada_este_turno", False):
            actions.append("ACTUALIZAR_MEMORIA")
        if not self.robot.get("memoria_consultada_este_turno", False):
            actions.append("CONSULTAR_MEMORIA")

        # 7. Navegación Inteligente hacia objetivos conocidos
        if not at_home:
            casa_exists = any(h.get("discovered") and h.get("terrain") == "casa" for h in self.hexes.values())
            if casa_exists:
                actions.append("MOVERSE_A_CASA")

        bosque_disp = any(h.get("discovered") and h.get("terrain") == "bosque" and h.get("agotado_hasta_minuto", 0) <= curr_min for h in self.hexes.values())
        if bosque_disp and curr_t != "bosque":
            actions.append("MOVERSE_A_BOSQUE")

        montaña_disp = any(h.get("discovered") and h.get("terrain") == "montaña" and h.get("agotado_hasta_minuto", 0) <= curr_min for h in self.hexes.values())
        if montaña_disp and curr_t != "montaña":
            actions.append("MOVERSE_A_MONTAÑA")

        pasto_disp = any(h.get("discovered") and h.get("terrain") == "pasto" and h.get("agotado_hasta_minuto", 0) <= curr_min for h in self.hexes.values())
        if pasto_disp and curr_t != "pasto":
            actions.append("MOVERSE_A_PASTO")

        water_exists = any(h.get("discovered") and h.get("terrain") == "agua" for h in self.hexes.values())
        if water_exists and not self.is_adjacent_to_water(rq, rr):
            actions.append("MOVERSE_A_AGUA")

        obras_exists = any(h.get("discovered") and h.get("terrain") == "en_obras" for h in self.hexes.values())
        if obras_exists:
            actions.append("MOVERSE_A_CONSTRUCCION")

        return actions

    def get_world_summary_for_ai(self) -> Dict[str, Any]:
        rq, rr = self.robot["q"], self.robot["r"]
        curr_hex = self.get_hex(rq, rr)
        adjacent = self.get_adjacent_info(rq, rr)

        # Mapa completo de hexágonos descubiertos agrupados por tipo
        mapa_conocido = {
            "casa": [],
            "en_obras": [],
            "montaña": [],
            "bosque": [],
            "pasto": [],
            "agua": []
        }
        total_descubiertos = 0
        curr_min = self.robot["minutos"]
        for h in self.hexes.values():
            if h.get("discovered"):
                total_descubiertos += 1
                t = h.get("terrain", "desconocido")
                coord = f"({h['q']},{h['r']})"
                if t == "en_obras":
                    coord += f" [Nvl {h.get('nivel_obras',1)}/10]"
                elif t in ("bosque", "pasto", "montaña"):
                    ag = h.get("agotado_hasta_minuto", 0)
                    if ag > curr_min:
                        coord += f" [Agotado: listo en {ag - curr_min}m]"
                    else:
                        coord += " [Disponible]"
                if t in mapa_conocido:
                    mapa_conocido[t].append(coord)
                else:
                    mapa_conocido[t] = [coord]

        at_home = self.is_at_home(rq, rr)
        nav = self.get_navigation_to_home(rq, rr)
        return {
            "posicion_actual": {"q": rq, "r": rr, "terreno": curr_hex["terrain"] if curr_hex else "desconocido"},
            "vida": f"{self.robot['vida']}/{self.robot['max_vida']}",
            "hambre": f"{self.robot['hambre']}/{self.robot['max_hambre']}",
            "sed": f"{self.robot['sed']}/{self.robot['max_sed']}",
            "inventario": list(self.robot["inventario"]),
            "max_inventario": self.robot["max_inventario"],
            "casa_almacen_items": list(self.robot["casa_almacen"]),
            "casa_almacen_ocupacion": f"{len(self.robot['casa_almacen'])}/{self.robot['max_casa_almacen']}",
            "max_casa_almacen": self.robot["max_casa_almacen"],
            "almacen_lleno": len(self.robot["casa_almacen"]) >= self.robot["max_casa_almacen"],
            "minutos_vividos": self.robot["minutos"],
            "iteracion": self.robot["iteracion"],
            "vecinos_adyacentes": adjacent,
            "adyacente_a_agua": self.is_adjacent_to_water(rq, rr),
            "en_casa": at_home,
            "navegacion_casa": nav,
            "total_hexagonos_descubiertos": total_descubiertos,
            "mapa_conocido": mapa_conocido,
            "memoria_archivo": self.get_memoria_robot(),
            "acciones_disponibles": self.get_available_actions()
        }

    def append_log_entry(self, entry: Dict[str, Any]):
        self.history.append(entry)
        self.save()
        # Escribir también en formato texto legible
        try:
            with open(TXT_LOG_FILE, "a", encoding="utf-8") as f:
                ts = entry.get("timestamp", "")
                f.write(f"\n[{ts}] ITERACIÓN {entry.get('iteracion')} - Minuto {entry.get('minuto')}\n")
                if "resumen_cronista" in entry:
                    f.write(f"CRONISTA: {entry['resumen_cronista']}\n")
                if "memoria_robot" in entry:
                    f.write(f"MENSAJE AL FUTURO: {entry['memoria_robot']}\n")
                for paso in entry.get("pasos", []):
                    f.write(f"  - Acción: {paso.get('accion')} | Exito: {paso.get('exito')} | {paso.get('mensaje')}\n")
                    if paso.get("comentario"):
                        f.write(f"    Comentario robot: \"{paso.get('comentario')}\"\n")
        except Exception as e:
            print(f"Error escribiendo en log txt: {e}")
