servidor_json_seedlink.py:34:        "modo": "servidor_json_seedlink_multicelda_v1_2",
servidor_json_seedlink.py:46:            "/sensores.json"
servidor_json_seedlink.py:83:@app.route("/sensores.json")
servidor_json_seedlink.py:84:def sensores_publicos():
servidor_json_seedlink.py:90:            "mensaje": "No existe todavía el catálogo de sensores",
servidor_json_seedlink.py:144:            "mensaje": f"No existe la célula {cell_id}",
servidor_json_seedlink.py:164:    print("Servidor Cuyum multicelda iniciado en http://127.0.0.1:5000", flush=True)
public_live.py:66:        "fuerte": "alta",
public_live.py:87:    if text in ("aviso", "anticipacion", "anticipación", "confirmacion", "confirmación"):
public_live.py:88:        return "aviso"
public_live.py:207:    for group_name in ("sensores", "reservas"):
public_live.py:230:    for key, s in (zona.get("sensores", {}) or {}).items():
public_live.py:254:    for key, s in (auto_state.get("sensores", {}) or {}).items():
public_live.py:380:            "sensors_active": _as_int(c.get("sensores_activos", c.get("sensors_active", 0))),
public_live.py:419:    alert_active = bool(event.get("sonar")) or str(event.get("level", "normal")).lower() not in ("normal", "observacion")
public_live.py:447:            "sensors_active": net.get("sensores_activos_total", 0),
public_live.py:448:            "sensors_calibrated": net.get("sensores_calibrados_total", 0),
public_live.py:454:            "sound": bool(event.get("sonar", False)),
event_journal.py:233:    for group_name in ("sensores", "reservas"):
event_journal.py:261:    for key, sensor in (zona.get("sensores", {}) or {}).items():
event_journal.py:273:    for key, sensor in (auto_state.get("sensores", {}) or {}).items():
event_journal.py:367:        summary = "señal compartida por sensores cercanos"
event_journal.py:438:    El estado vivo ya está en /api/public/live. Si copiamos cada arranque,
event_journal.py:449:    sound = bool(event.get("sonar", False))
event_journal.py:451:    sensors_active = network.get("sensores_activos_total")
event_journal.py:459:        "public_level": "aviso" if sound else "movimiento_posible",
event_journal.py:498:    # - coincidencia de célula: siempre importa;
event_journal.py:508:        summary = "señal compartida por sensores cercanos"
event_journal.py:614:    # Snapshots de red/célula, calibración y latencia son estado vivo o auditoría interna.
multicell_fusion.py:11:# Si pasa de este tiempo, la célula no se considera viva para decisión.
multicell_fusion.py:101:def _ratio_max_from_sensors(sensores):
multicell_fusion.py:103:    for sensor in (sensores or {}).values():
multicell_fusion.py:108:def _max_effective_warning(sensores):
multicell_fusion.py:110:    for sensor in (sensores or {}).values():
multicell_fusion.py:115:def _best_direction_from_sensors(sensores):
multicell_fusion.py:117:    for sensor in (sensores or {}).values():
multicell_fusion.py:128:    for sensor in sorted((sensores or {}).values(), key=lambda x: _as_int(x.get("prioridad", 999), 999)):
multicell_fusion.py:146:def _safe_message(message, estaciones_confirmando=0, sonar=False):
multicell_fusion.py:151:        if sonar:
multicell_fusion.py:153:        if _as_int(estaciones_confirmando, 0) >= 2:
multicell_fusion.py:155:        if _as_int(estaciones_confirmando, 0) == 1:
multicell_fusion.py:161:def _display_state_label(estado, estaciones_confirmando=0, sonar=False):
multicell_fusion.py:163:    if sonar:
multicell_fusion.py:164:        return "aviso"
multicell_fusion.py:166:        if _as_int(estaciones_confirmando, 0) >= 2:
multicell_fusion.py:174:def classify_cell(sensores_activos, fresh=True):
multicell_fusion.py:177:    6+ = célula alta
multicell_fusion.py:178:    4-5 = célula buena
multicell_fusion.py:179:    2-3 = célula mínima digna
multicell_fusion.py:183:    n = _as_int(sensores_activos, 0)
multicell_fusion.py:202:    # Una célula mínima informa vigilancia, pero no debería hacer sonar sola.
multicell_fusion.py:221:        "sensores_activos": 0,
multicell_fusion.py:222:        "sensores_calibrados": 0,
multicell_fusion.py:225:        "estaciones_confirmando": 0,
multicell_fusion.py:226:        "estaciones_confirmando_lista": [],
multicell_fusion.py:239:    cell_class = classify_cell(cell.get("sensores_activos", 0), cell.get("fresh", False))
multicell_fusion.py:245:        cell.get("estado"), cell.get("estaciones_confirmando", 0), False
multicell_fusion.py:262:    sensores = zona.get("sensores", {})
multicell_fusion.py:264:    estaciones_confirmando = _as_int(zona.get("estaciones_confirmando", 0), 0)
multicell_fusion.py:273:        "sensores_activos": _as_int(zona.get("sensores_activos", calidad.get("sensores_activos", 0) if isinstance(calidad, dict) else 0)),
multicell_fusion.py:274:        "sensores_calibrados": _as_int(zona.get("sensores_calibrados", calidad.get("sensores_calibrados", 0) if isinstance(calidad, dict) else 0)),
multicell_fusion.py:277:        "estaciones_confirmando": estaciones_confirmando,
multicell_fusion.py:278:        "estaciones_confirmando_lista": zona.get("estaciones_confirmando_lista", []),
multicell_fusion.py:279:        "ratio_max": _as_float(zona.get("ratio_max", 0), _ratio_max_from_sensors(sensores)),
multicell_fusion.py:284:    cell["display_state_label"] = _display_state_label(raw_estado, estaciones_confirmando, False)
multicell_fusion.py:294:    sensores = auto_data.get("sensores", {})
multicell_fusion.py:297:    # Preferir campos superiores del lector; si faltan, usar calidad_red; si faltan, contar sensores activos/calibrados.
multicell_fusion.py:298:    sensores_activos = auto_data.get("sensores_activos")
multicell_fusion.py:299:    sensores_calibrados = auto_data.get("sensores_calibrados")
multicell_fusion.py:300:    if sensores_activos is None and isinstance(calidad, dict):
multicell_fusion.py:301:        sensores_activos = calidad.get("sensores_activos")
multicell_fusion.py:302:    if sensores_calibrados is None and isinstance(calidad, dict):
multicell_fusion.py:303:        sensores_calibrados = calidad.get("sensores_calibrados")
multicell_fusion.py:304:    if sensores_activos is None:
multicell_fusion.py:305:        sensores_activos = sum(1 for s in sensores.values() if s.get("estado_sensor") == "activo")
multicell_fusion.py:306:    if sensores_calibrados is None:
multicell_fusion.py:307:        sensores_calibrados = sum(1 for s in sensores.values() if s.get("calibrado"))
multicell_fusion.py:309:    direction_label = _best_direction_from_sensors(sensores)
multicell_fusion.py:325:        "sensores_activos": _as_int(sensores_activos, 0),
multicell_fusion.py:326:        "sensores_calibrados": _as_int(sensores_calibrados, 0),
multicell_fusion.py:327:        "anticipacion_activos": _as_int(sensores_activos, 0),
multicell_fusion.py:329:        "estaciones_confirmando": _as_int(auto_data.get("estaciones_confirmando", 0)),
multicell_fusion.py:330:        "estaciones_confirmando_lista": auto_data.get("estaciones_confirmando_lista", []),
multicell_fusion.py:331:        "ratio_max": _ratio_max_from_sensors(sensores),
multicell_fusion.py:332:        "effective_warning_seconds": _max_effective_warning(sensores),
multicell_fusion.py:360:            "sensors_active": _as_int(c.get("sensores_activos", 0), 0),
multicell_fusion.py:361:            "sensors_calibrated": _as_int(c.get("sensores_calibrados", 0), 0),
multicell_fusion.py:362:            "confirming": _as_int(c.get("estaciones_confirmando", 0), 0),
multicell_fusion.py:382:    active_cells = [c for c in cells if c.get("fresh") and _as_int(c.get("sensores_activos", 0)) > 0]
multicell_fusion.py:395:    sensores_activos_total = sum(_as_int(c.get("sensores_activos", 0)) for c in active_cells)
multicell_fusion.py:396:    sensores_calibrados_total = sum(_as_int(c.get("sensores_calibrados", 0)) for c in active_cells)
multicell_fusion.py:397:    estaciones_confirmando_total = sum(_as_int(c.get("estaciones_confirmando", 0)) for c in active_cells)
multicell_fusion.py:405:        network_quality = "multicelda_fuerte"
multicell_fusion.py:406:        network_label = "red multicelda alta"
multicell_fusion.py:409:        network_quality = "multicelda_parcial"
multicell_fusion.py:410:        network_label = "red multicelda parcial"
multicell_fusion.py:418:        network_label = "solo célula remota activa"
multicell_fusion.py:428:    # Regla prudente: una célula mínima no dispara sola. Strong/good puede generar anticipación experimental si confirma internamente.
multicell_fusion.py:431:        if c.get("flag") and _as_int(c.get("estaciones_confirmando", 0)) >= 2
multicell_fusion.py:435:        if c.get("flag") and _as_int(c.get("estaciones_confirmando", 0)) >= 2
multicell_fusion.py:439:    local_raw_sonar = bool(local_esp32.get("sonar", False))
multicell_fusion.py:440:    local_confirming = _as_int(local.get("estaciones_confirmando", 0), 0)
multicell_fusion.py:441:    local_flag = bool(local.get("fresh") and (local.get("flag") or local_raw_sonar))
multicell_fusion.py:444:    event_message = "normal multicelda" if network_mode.startswith("multicell") else "normal"
multicell_fusion.py:445:    sonar = False
multicell_fusion.py:451:        if local_raw_sonar:
multicell_fusion.py:453:            event_message = _safe_message(local_esp32.get("mensaje"), local_confirming, sonar=True)
multicell_fusion.py:454:            sonar = True
multicell_fusion.py:460:            sonar = False
multicell_fusion.py:466:            sonar = False
multicell_fusion.py:471:        event_level = "anticipacion_multicelda"
multicell_fusion.py:473:        sonar = True
multicell_fusion.py:478:        event_level = "vigilancia_multicelda"
multicell_fusion.py:480:        sonar = False
multicell_fusion.py:485:    display_status = _display_state_label(event_level, estaciones_confirmando_total, sonar)
multicell_fusion.py:486:    display_message = _safe_message(event_message, estaciones_confirmando_total, sonar)
multicell_fusion.py:508:            "sound": sonar,
multicell_fusion.py:528:            "sensores_activos_total": sensores_activos_total,
multicell_fusion.py:529:            "sensores_calibrados_total": sensores_calibrados_total,
multicell_fusion.py:530:            "estaciones_confirmando_total": estaciones_confirmando_total,
multicell_fusion.py:536:            "sonar": sonar,
multicell_fusion.py:560:        "sonar": event["sonar"],
multicell_fusion.py:567:        "sensores_activos": net["sensores_activos_total"],
multicell_fusion.py:568:        "sensores_calibrados": net["sensores_calibrados_total"],
multicell_fusion.py:570:            _as_int(c.get("sensores_activos", 0))
multicell_fusion.py:575:        "estaciones_confirmando": net["estaciones_confirmando_total"],
multicell_fusion.py:579:        # Campos portables para ESP32 multicelda.
multicell_fusion.py:585:        # Campos multicelda nuevos: el ESP32 actual los ignora; el próximo sketch los puede mostrar.
multicell_fusion.py:607:        "cell_00_sensores_activos": local.get("sensores_activos", 0),
multicell_fusion.py:613:        "auto_cell_01_sensores_activos": auto01.get("sensores_activos", 0),
multicell_fusion.py:614:        "auto_cell_01_aviso_util": auto01.get("effective_warning_seconds", 0),
auto_cell_reader_seedlink.py:51:    sensores = []
auto_cell_reader_seedlink.py:52:    for s in data.get('sensores', []):
auto_cell_reader_seedlink.py:55:        sensores.append(s)
auto_cell_reader_seedlink.py:56:    return server, sensores, data
auto_cell_reader_seedlink.py:59:def calcular_calidad_red(estado_sensores, minimo=5):
auto_cell_reader_seedlink.py:60:    sensores = list(estado_sensores.values())
auto_cell_reader_seedlink.py:61:    calibrados = [s for s in sensores if s.get('calibrado')]
auto_cell_reader_seedlink.py:65:        estado = 'fuerte'
auto_cell_reader_seedlink.py:76:        'sensores_activos': total,
auto_cell_reader_seedlink.py:77:        'sensores_calibrados': len(calibrados),
auto_cell_reader_seedlink.py:84:    fuerte = any(x.get('flag_fuerte') for x in flags.values())
auto_cell_reader_seedlink.py:86:        return 'observacion_externa_fuerte'
auto_cell_reader_seedlink.py:89:    if cantidad == 1 and fuerte:
auto_cell_reader_seedlink.py:97:    def __init__(self, server, sensores, inventario, output_path):
auto_cell_reader_seedlink.py:100:        self.sensores = sensores
auto_cell_reader_seedlink.py:107:        self.estado_sensores = {}
auto_cell_reader_seedlink.py:109:        self.mapa = {clave_sensor_cfg(s): s for s in sensores}
auto_cell_reader_seedlink.py:122:            self.estado_sensores[clave] = self.estado_base(trace.id, clave, cfg, 'latencia_alta', False, latencia, energia, magnitud)
auto_cell_reader_seedlink.py:138:                self.estado_sensores[clave] = st
auto_cell_reader_seedlink.py:146:        flag_fuerte = ratio >= FACTOR_FLAG_FUERTE
auto_cell_reader_seedlink.py:162:                'flag_fuerte': flag_fuerte,
auto_cell_reader_seedlink.py:167:        self.estado_sensores[clave] = {
auto_cell_reader_seedlink.py:184:            'flag_fuerte': flag_fuerte,
auto_cell_reader_seedlink.py:192:        print(f'{trace.id} energia={round(energia,2)} base={round(base_sensor,2)} ratio={round(ratio,2)} flag={flag} fuerte={flag_fuerte}')
auto_cell_reader_seedlink.py:209:            'flag_fuerte': False,
auto_cell_reader_seedlink.py:222:        calidad = calcular_calidad_red(self.estado_sensores, self.inventario.get('min_good_sensors', 5))
auto_cell_reader_seedlink.py:238:            'sensores_totales': len(self.sensores),
auto_cell_reader_seedlink.py:239:            'sensores_activos': calidad['sensores_activos'],
auto_cell_reader_seedlink.py:240:            'sensores_calibrados': calidad['sensores_calibrados'],
auto_cell_reader_seedlink.py:241:            'estaciones_confirmando': len(self.flags_recientes),
auto_cell_reader_seedlink.py:242:            'estaciones_confirmando_lista': list(self.flags_recientes.keys()),
auto_cell_reader_seedlink.py:244:            'sensores': self.estado_sensores
auto_cell_reader_seedlink.py:260:    server, sensores, inventario = cargar_inventario(inv_path)
auto_cell_reader_seedlink.py:267:    print('Sensores cargados:', len(sensores))
auto_cell_reader_seedlink.py:270:    client = AutoCellReader(server, sensores, inventario, out_path)
auto_cell_reader_seedlink.py:271:    for sensor in sensores:
zona_grupo_01_seedlink_adaptativo_v2.py:32:    sensores = []
zona_grupo_01_seedlink_adaptativo_v2.py:33:    for s in data.get("sensores", []):
zona_grupo_01_seedlink_adaptativo_v2.py:39:        sensores.append(s)
zona_grupo_01_seedlink_adaptativo_v2.py:41:    return servidor, sensores, data
zona_grupo_01_seedlink_adaptativo_v2.py:73:def calcular_calidad_red(estado_sensores):
zona_grupo_01_seedlink_adaptativo_v2.py:74:    sensores = list(estado_sensores.values())
zona_grupo_01_seedlink_adaptativo_v2.py:76:    calibrados = [s for s in sensores if s.get("calibrado")]
zona_grupo_01_seedlink_adaptativo_v2.py:107:        "sensores_activos": total_activos,
zona_grupo_01_seedlink_adaptativo_v2.py:108:        "sensores_calibrados": len(calibrados),
zona_grupo_01_seedlink_adaptativo_v2.py:114:def nivel_por_evento(estaciones_confirmando, hay_flag_fuerte_anticipacion):
zona_grupo_01_seedlink_adaptativo_v2.py:115:    cantidad = len(estaciones_confirmando)
zona_grupo_01_seedlink_adaptativo_v2.py:121:        return "aviso_interno"
zona_grupo_01_seedlink_adaptativo_v2.py:123:    if cantidad == 1 and hay_flag_fuerte_anticipacion:
zona_grupo_01_seedlink_adaptativo_v2.py:124:        return "aviso_interno"
zona_grupo_01_seedlink_adaptativo_v2.py:135:            "sonar": False,
zona_grupo_01_seedlink_adaptativo_v2.py:143:    if nivel in ["aviso_interno", "critico_experimental"]:
zona_grupo_01_seedlink_adaptativo_v2.py:145:            "sonar": True,
zona_grupo_01_seedlink_adaptativo_v2.py:155:            "sonar": False,
zona_grupo_01_seedlink_adaptativo_v2.py:164:        "sonar": False,
zona_grupo_01_seedlink_adaptativo_v2.py:176:    if nivel == "aviso_interno":
zona_grupo_01_seedlink_adaptativo_v2.py:184:    def __init__(self, server, sensores, inventario):
zona_grupo_01_seedlink_adaptativo_v2.py:188:        self.sensores = sensores
zona_grupo_01_seedlink_adaptativo_v2.py:193:        self.estado_sensores = {}
zona_grupo_01_seedlink_adaptativo_v2.py:196:        self.mapa_sensores = {}
zona_grupo_01_seedlink_adaptativo_v2.py:197:        for s in self.sensores:
zona_grupo_01_seedlink_adaptativo_v2.py:198:            self.mapa_sensores[clave_sensor_cfg(s)] = s
zona_grupo_01_seedlink_adaptativo_v2.py:204:        if clave not in self.mapa_sensores:
zona_grupo_01_seedlink_adaptativo_v2.py:207:        cfg = self.mapa_sensores[clave]
zona_grupo_01_seedlink_adaptativo_v2.py:216:            self.estado_sensores[clave] = {
zona_grupo_01_seedlink_adaptativo_v2.py:228:                "flag_fuerte": False,
zona_grupo_01_seedlink_adaptativo_v2.py:249:                self.estado_sensores[clave] = {
zona_grupo_01_seedlink_adaptativo_v2.py:267:                    "flag_fuerte": False,
zona_grupo_01_seedlink_adaptativo_v2.py:283:        flag_fuerte_crudo = ratio >= FACTOR_FLAG_FUERTE
zona_grupo_01_seedlink_adaptativo_v2.py:286:        flag_fuerte = flag_fuerte_crudo and puede_disparar
zona_grupo_01_seedlink_adaptativo_v2.py:306:                "flag_fuerte": flag_fuerte,
zona_grupo_01_seedlink_adaptativo_v2.py:313:        self.estado_sensores[clave] = {
zona_grupo_01_seedlink_adaptativo_v2.py:332:            "flag_fuerte": flag_fuerte,
zona_grupo_01_seedlink_adaptativo_v2.py:343:            f"flag={flag} fuerte={flag_fuerte}"
zona_grupo_01_seedlink_adaptativo_v2.py:358:        estaciones_confirmando = list(self.flags_recientes.keys())
zona_grupo_01_seedlink_adaptativo_v2.py:360:        hay_flag_fuerte_anticipacion = False
zona_grupo_01_seedlink_adaptativo_v2.py:369:                data["flag_fuerte"]
zona_grupo_01_seedlink_adaptativo_v2.py:372:                hay_flag_fuerte_anticipacion = True
zona_grupo_01_seedlink_adaptativo_v2.py:375:            estaciones_confirmando,
zona_grupo_01_seedlink_adaptativo_v2.py:376:            hay_flag_fuerte_anticipacion
zona_grupo_01_seedlink_adaptativo_v2.py:379:        calidad_red = calcular_calidad_red(self.estado_sensores)
zona_grupo_01_seedlink_adaptativo_v2.py:383:            mensaje = "Crítico experimental: varias estaciones independientes confirmando"
zona_grupo_01_seedlink_adaptativo_v2.py:384:        elif nivel == "aviso_interno":
zona_grupo_01_seedlink_adaptativo_v2.py:399:            "sensores_totales": len(self.sensores),
zona_grupo_01_seedlink_adaptativo_v2.py:400:            "sensores_calibrados": calidad_red["sensores_calibrados"],
zona_grupo_01_seedlink_adaptativo_v2.py:401:            "sensores_activos": calidad_red["sensores_activos"],
zona_grupo_01_seedlink_adaptativo_v2.py:402:            "sensores_con_flag": sum(
zona_grupo_01_seedlink_adaptativo_v2.py:403:                1 for s in self.estado_sensores.values()
zona_grupo_01_seedlink_adaptativo_v2.py:406:            "estaciones_confirmando": len(estaciones_confirmando),
zona_grupo_01_seedlink_adaptativo_v2.py:407:            "estaciones_confirmando_lista": estaciones_confirmando,
zona_grupo_01_seedlink_adaptativo_v2.py:412:            "sonar": esp32["sonar"],
zona_grupo_01_seedlink_adaptativo_v2.py:417:            "sensores": self.estado_sensores
zona_grupo_01_seedlink_adaptativo_v2.py:453:    servidor, sensores, inventario = cargar_inventario()
zona_grupo_01_seedlink_adaptativo_v2.py:460:    print("Sensores cargados:", len(sensores))
zona_grupo_01_seedlink_adaptativo_v2.py:463:    client = LectorSeedLinkAdaptativo(servidor, sensores, inventario)
zona_grupo_01_seedlink_adaptativo_v2.py:465:    for sensor in sensores:
sensor_auditor.py:52:    for s in (inventory or {}).get("sensores", []):
sensor_auditor.py:284:    current_sensors = zone.get("sensores", {}) or {}
sensor_auditor.py:360:    print(f"Auditor actualizado: {len(catalog['sensors'])} sensores | cambios_estado={len(changed_states)}", flush=True)
descubridor_seedlink.py:102:    sensores = inventario.get("sensores", [])
descubridor_seedlink.py:105:    for s in sensores:
descubridor_seedlink.py:123:    for s in sensores:
descubridor_seedlink.py:152:    for s in sensores:
descubridor_seedlink.py:195:    for s in sensores:
generar_inventory_auto_cell_01.py:90:        'sensores': sensors,
cuyum_auto_cells.py:9:- Construir células externas desde sensores que ya demostraron respirar por SeedLink.
cuyum_auto_cells.py:10:- No crear células que no puedan dar al menos 10 s útiles de aviso.
cuyum_auto_cells.py:11:- Evitar solapamiento de sensores principales.
cuyum_auto_cells.py:161:        "message": "Zona local/control. No cuenta como anticipación; sirve para aviso inmediato, coherencia y scoring."
cuyum_auto_cells.py:309:            "message": "Célula generada automáticamente desde sensores SeedLink vivos y sin solapar sensores principales."
cuyum_auto_cells.py:322:    lines.append("Default de diseño: auto-celdas desde sensores vivos, sin solapar principales.")
cuyum_auto_cells.py:328:    lines.append(f"Sensores por célula: {cfg['sensors_per_cell']} | mínimo: {cfg['min_sensors_per_cell']}")
cuyum_auto_cells.py:337:            lines.append(f"Dirección={cell.get('direction')} | distancia_home={cell.get('distance_from_home_km')} km | aviso_útil≈{cell.get('effective_warning_seconds')} s")
cuyum_auto_cells.py:344:                extra = f" packets={s.get('packets','?')} lat={s.get('latency_seconds','?')}s dir={s.get('direction','?')} aviso={s.get('effective_warning_seconds','?')}s"
cuyum_auto_cells.py:385:            "reason": "no se encontró otro grupo de sensores SeedLink vivos, suficientemente separado y con al menos 10 s útiles de aviso"
cuyum_auto_cells.py:420:        "warning_rule": "Las células early_warning requieren al menos 10 segundos útiles estimados; si no, quedan fuera o como local/control.",
iniciar_cuyum_visible_v1_2.sh:55:echo "Iniciando servidor Flask multicelda..."
iniciar_cuyum_visible_v1_2.sh:75:echo "Iniciando auditor de sensores..."
iniciar_cuyum_visible_v1_2.sh:111:echo "Para mirar red multicelda: ./ver_multicelda_v1_2.sh"
detener_cuyum_v1_2.sh:24:echo "Si no aparece nada arriba, Cuyum quedó apagado."
ver_multicelda_v1_2.sh:39:            "sensores_activos", "sensores_calibrados", "cells_active",
ver_multicelda_v1_2.sh:42:            "cell_00_class", "cell_00_fresh", "cell_00_sensores_activos",
ver_multicelda_v1_2.sh:43:            "auto_cell_01_class", "auto_cell_01_fresh", "auto_cell_01_sensores_activos", "auto_cell_01_aviso_util",
ver_multicelda_v1_2.sh:44:            "sonar", "buzzer_segundos", "led_nivel", "ratio_max"
ver_multicelda_v1_2.sh:52:                extra = f" aviso={c.get('warning_seconds')}s"
ver_multicelda_v1_2.sh:55:                f"estado={c.get('state_label'):13} sensores={c.get('sensors_active')}/{c.get('sensors_calibrated')} "
ver_multicelda_v1_2.sh:70:        print("sensores_activos_total:", net.get("sensores_activos_total"))
ver_multicelda_v1_2.sh:71:        print("sensores_calibrados_total:", net.get("sensores_calibrados_total"))
ver_multicelda_v1_2.sh:72:        print("estaciones_confirmando_total:", net.get("estaciones_confirmando_total"))
ver_multicelda_v1_2.sh:81:                f"fresh={c.get('fresh')} activos={c.get('sensores_activos')} "
ver_multicelda_v1_2.sh:82:                f"cal={c.get('sensores_calibrados')} quality={c.get('calidad_red')} "
arrancar_sistema_v1_2.sh:32:echo "Iniciando servidor Flask multicelda..."
arrancar_sistema_v1_2.sh:56:echo "Iniciando auditor de sensores Cuyum..."
arrancar_sistema_v1_2.sh:61:echo "Sistema multicelda iniciado."
