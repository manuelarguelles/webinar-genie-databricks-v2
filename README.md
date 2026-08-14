# Databricks Genie en producción — edición 2

Material del webinar **«Tu Genie no está roto: le falta contexto»**, segunda edición
(14-ago-2026). Taller-teaser del programa *Databricks AI Engineer* (8 sesiones).

**Ponente:** Manuel Argüelles · AI Engineer

La primera edición (23-jul-2026) está en
[`manuelarguelles/webinar-genie-databricks`](https://github.com/manuelarguelles/webinar-genie-databricks)
· [grabación en YouTube](https://www.youtube.com/watch?v=Fm78sGfU2ks).

---

## Qué cambia respecto de la edición 1

| | edición 1 | edición 2 |
|---|---|---|
| Plataforma | Azure (sandbox) | **Databricks on AWS** (`us-west-2`) |
| Genie spaces | 2 (ventas crudo + curado) | **4** — se suman **Inventario** y **Radar comercial** |
| A/B | curar y descurar en vivo (rollback) | **lado a lado**, un catálogo por mitad, sin rollback |
| Demo 0 | «margen −23.055,30 = pérdida» | «margen **267.868,18**» = la venta neta con otro nombre |
| Preguntas verificadas | 6 | **21**, todas transcritas |
| Spaces creados | a mano por la UI | **por API**, sin un solo clic |

La tesis nueva de esta edición: **un Genie curado no alcanza — se gobierna un portafolio.**
Cada dominio tiene su propia trampa, y no se parecen entre sí.

---

## Los cuatro spaces

| space | catálogo | estado | su trampa |
|---|---|---|---|
| **Ventas Neptuno** | `neptuno` | **CRUDO a propósito** | el Demo 0: se lo ve fallar |
| **Ventas Neptuno AI** | `neptuno_ai` | curado | una métrica que **no existe** (margen sin costos) |
| **Inventario Neptuno** | `neptuno_ai` | curado | una **columna olvidada** (`UnidadesEnPedido`) → 17 vs **2** |
| **Radar Comercial** | `neptuno_ai` | curado | una **comparación injusta** (año parcial) → 48 vs **23** |

📏 **Regla:** todo space curado va sobre `neptuno_ai`; solo el del Demo 0 se queda en `neptuno`.
Los `COMMENT` son **globales al metastore** y las instrucciones son **locales al space**: si
documentas `neptuno` para curar inventario, curas también el Demo 0 y te quedas sin demo.

---

## Contenido

```
deck/    webinar-genie-v2-DECK.html   26 slides · P presenta, ← → navega, F fullscreen
                                      ★ arriba a la derecha = chivato del presentador
guia/    taller-v2.html               consola del taller · 6 pestañas · SQL copiable
sql/     capas.sql                    capas 1, 5 y 6 desde la óptica de ventas
         capas-inventario.sql         capa 1 del dominio inventario (solo neptuno_ai)
scripts/ bootstrap.py                 reconstruye Neptuno de cero + verificación por efecto
         montar_ai.py                 clona a neptuno_ai y aplica las capas
         crear_tablas.py              tablas desnudas (también sirve de rollback)
         ventas_ai_space.py           crea/actualiza el space de ventas curado
         inventario_space.py          ídem inventario
         radar_space.py               ídem radar comercial
         ab.py                        misma pregunta a los dos spaces, en paralelo
         probar_preguntas.py          Conversation API · devuelve respuesta + SQL
         convertir.py · ajustar.py    Northwind → Neptuno (ES, fechas +28 años)
docs/    BANCO-PREGUNTAS.md           ★ las 21 preguntas con su respuesta textual
         inventario-preguntas.md      trampas medidas del dominio inventario
         radar-preguntas.md           trampas medidas del radar comercial
         genie-space.md               capas 2, 3 y 4 listas para pegar
         instrucciones-ai.txt         el bloque de instrucciones del space curado
csv/     los 8 CSVs de Neptuno
terraform/  catálogo, schema, volumen y warehouse
```

**Empieza por `docs/BANCO-PREGUNTAS.md`** — dice qué responde cada space a cada pregunta.
Ese archivo *es* el set de oro del que habla el slide 20.

---

## El dataset

**Neptuno** — importador ficticio de alimentos gourmet (Northwind traducido al español).
830 pedidos · 2.155 líneas · jul-2024 → **corte 2026-05-06**. 2025 es un año completo
(408 pedidos), así que «el año pasado» funciona.

Modelo estrella: hecho `detalles_pedidos` + `pedidos`; dimensiones `productos` → `categorias`,
`clientes`, `empleados`, `proveedores`, `transportistas`.

### Las trampas del modelo

| # | trampa | la cura |
|---|---|---|
| 1 | **Descuento olvidado** — 838 de 2.155 líneas (39 %) tienen descuento | capa 1 → capa 3 → capa 5 |
| 2 | `FechaPedido` vs `FechaEnvio` vs `FechaEntrega`; 21 pedidos sin enviar | capas 1 y 2 |
| 3 | `Cargo` (flete) parece ingreso, es costo | capa 1 |
| 4 | `PrecioUnidad` está en **dos** tablas: histórico vs catálogo | capa 1 |
| 5 | `Suspendido` (1/0) sin explicar — 10 productos descontinuados | capa 1 |
| 6 | JOINs sin declarar → duplicación silenciosa de filas | capa 6 |
| 7 | Sinónimos: facturación / ingresos / revenue | capa 4 |
| 8 | **`UnidadesEnPedido`** — lo que ya viene en camino | `capas-inventario.sql` |
| 9 | **El corte de datos no es hoy** — 100 días de desfase | trusted queries del radar |

---

## Reproducirlo en tu propio workspace

Todo se configura por variables de entorno. **No hay credenciales en este repo.**

```bash
export GENIE_PROFILE=tu-perfil          # perfil de ~/.databrickscfg
export GENIE_WAREHOUSE=<warehouse_id>
export GENIE_CATALOG=neptuno
export GENIE_CATALOG_AI=neptuno_ai
export GENIE_SCHEMA=ventas

cd scripts
python3 bootstrap.py                    # catálogo + volumen + 8 tablas DESNUDAS + verificación
python3 montar_ai.py                    # clona a neptuno_ai y aplica capas 1/5/6
python3 dbsql.py < ../sql/capas-inventario.sql
python3 ventas_ai_space.py              # crea los spaces curados
python3 inventario_space.py
python3 radar_space.py
```

`bootstrap.py` **verifica por efecto**: si estas cuatro cifras no salen, algo se rompió.

| | |
|---|---|
| Bebidas 2025 | **103.924,31** |
| Venta neta 2025 | **617.085,20** |
| Pedidos · líneas | **830** · **2.155** |

Probar una pregunta contra un space:

```bash
GENIE_SPACE=<space_id> python3 probar_preguntas.py "¿Qué productos tengo que reponer?"
```

---

## Gotchas que costaron tiempo

- 🔑 **Que un workspace responda no prueba que haya compute.** El control plane de Databricks
  contesta con la suscripción muerta; el warehouse se queda en `STARTING` para siempre
  (medido: 22 minutos).
- 🔑 **Un PAT puede crearse sin scopes y no avisar.** Falla recién al primer uso, con
  `Provided access token does not have required scopes: sql`. Scopes necesarios:
  `sql`, `files`, `unity-catalog`, `genie`, `workspace`.
- 🔑 **Los spaces SÍ se crean por API.** `POST /api/2.0/genie/spaces` con `serialized_space`.
  Dos detalles del proto: `example_question_sqls` **no acepta `content`** (la descripción va
  como comentario `--` al tope del SQL) y los `id` deben ser **UUID de 32 hex en minúscula
  y sin guiones**.
- ⚠️ **Los importes cambian de centavos entre spaces.** El curado usa `venta_neta()` y cierra
  en `617.085,33` / `103.924,32`; el cálculo directo del crudo da `617.085,20` / `103.924,31`.
  Es redondeo de la función, no un error — pero no los muestres juntos sin explicarlo.
- ⚠️ `python3 dbsql.py < ../sql/capas.sql` termina con un `PARSE_SYNTAX_ERROR` **inofensivo**:
  el runner intenta ejecutar el bloque final de comentarios del ROLLBACK. Las capas se
  aplican todas bien.

---

## El curso

**Databricks AI Engineer** — 8 sesiones en vivo, de Data Engineer a AI Engineer.
Proyecto integrador: **«Copiloto de Datos»**. Lo de este webinar es una rebanada de ese proyecto.
