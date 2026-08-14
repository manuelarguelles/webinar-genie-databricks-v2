# Genie Space «Inventario Neptuno» — CURADO · preguntas validadas

**Space:** `01f197a1f44d173a824fb4810124d4c6`
→ https://dbc-fba20ab2-d1fc.cloud.databricks.com/genie/rooms/01f197a1f44d173a824fb4810124d4c6

Creado y curado por API con `inventario_space.py` (reproducible: `--update <space_id>` re-aplica
la curación sin duplicar nada, porque los ids se derivan por hash del contenido).

**Por qué este caso:** «Inventario» es uno de los 11 tipos de Genie con **demanda real
verificada** (cliente con nombre y cifra pública): HP con miles de SKU, Casas Bahia, Conagra.

**Catálogo:** **`neptuno_ai`** (el curado) · **Tablas:** `productos`, `categorias`,
`proveedores`, `detalles_pedidos`, `pedidos`.

---

## 📏 Va sobre `neptuno_ai`, no sobre `neptuno`

**Todo space curado se apoya en el catálogo curado.** Así hereda la capa 1 (COMMENT), la 5
(UC functions) y la 6 (PK/FK) que ya aplicó `montar_ai.py`, y sólo agrega lo que vive en el
space: instrucciones, SQL de confianza y preguntas sugeridas.

⚠️ Los `COMMENT` son **globales al metastore**. Ponerlos en `neptuno` habría curado también al
space crudo «Ventas Neptuno» y **arruinado el Demo 0**; en `neptuno_ai` no hay riesgo porque es
un catálogo aparte, clonado justamente para estar curado. Sólo el space del Demo 0 se queda
en `neptuno`.

📌 `capas.sql` documenta el modelo desde la óptica de **ventas** y deja sin comentar
`UnidadesEnPedido` y `NivelNuevoPedido` — las dos de las que depende la reposición. Ese hueco
lo cierra [`capas-inventario.sql`](capas-inventario.sql), que se aplica **sólo a `neptuno_ai`**.

---

## La trampa que cura este space

> **P: «¿Qué productos tengo que reponer?»**

| | respuesta | por qué |
|---|---|---|
| **Sin curar** | **17 productos** | compara sólo `UnidadesEnExistencia <= NivelNuevoPedido` |
| **Curado** | **2 productos** | descuenta `UnidadesEnPedido`: lo que **ya viene en camino** |
| | **16 falsos positivos** | pediría 8× más mercadería de la necesaria |

El ejemplo estrella: **Gorgonzola Telino** — 0 en existencia, punto de reorden 20, pero **70
unidades ya pedidas**. El Genie crudo lo lista como «el más urgente» y, en la misma respuesta,
**muestra el 70 en pedido sin darse cuenta de que contradice su conclusión.**

---

## Las 6 preguntas sugeridas — respuestas verificadas (14-ago-2026)

### 1. ¿Qué productos tengo que reponer?
> Debes reponer: **Nord-Ost Matjeshering** (Pescados y Mariscos) y **Outback Lager** (Bebidas).
> Ambos con un faltante de 5 unidades respecto a su punto de reorden.

**2 productos**, no 17. ✅

### 2. ¿Cuál es mi nivel de inventario?
> Nivel vigente **2.962 unidades** · stock muerto **157** · total bruto **3.119**.

Separa el stock muerto en vez de inflar el número. ✅

### 3. ¿Qué productos están agotados?
> **Gorgonzola Telino** (Lacteos) está agotado, pero tiene **70 unidades en camino** y su
> situación es **reposición en curso**. No es necesario reabastecer este artículo, ya que la
> reposición está resuelta.

✅ Da resultado **y** el matiz: distingue «agotado» de «desatendido» en una sola respuesta.
Es además el mismo producto con el que el space crudo se equivoca, así que sirve de puente
entre los dos casos.

📌 **El dato fino:** hay **5 productos con existencia 0**, pero sólo **1 es vigente**
(Gorgonzola Telino); los otros **4 son descontinuados** y por eso no aparecen — se filtran con
`Suspendido = 0`. La versión anterior de esta pregunta («…y no tienen reposición en curso»)
devolvía vacío y se cambió por ésta.

### 4. ¿Cuántos días de cobertura tengo por producto?
> **Gorgonzola Telino 0 días** · Sir Rodney's Scones 1,8 · … · Grandma's Boysenberry Spread **438**
> · Laughing Lumberjack Lager 292. El rango va de 0 a 438 días.

Cruza inventario con demanda real de 2025. ✅

### 5. ¿Cuánto vale mi inventario por categoría?
> Pescados y Mariscos **13.010,35** · Condimentos **11.926,05** · Bebidas **11.365,25** ·
> Lácteos 11.271,20 · Repostería 10.392,20 … menor: Frutas y Verduras 2.363,75.
> *«recuerda que esto no es costo ni valor contable, porque el modelo no incluye costos»*

🔑 **La aclaración salió sola**, por la instrucción de valoración. Es el mismo límite del Demo 0
del otro space, pero acá el Genie lo dice **antes de que se lo pregunten**.

### 6. ¿Qué productos descontinuados siguen ocupando almacén?
> Chai (Bebidas) **39 u** · Mishi Kobe Niku 29 · Rössle Sauerkraut 26 ·
> Singaporean Hokkien Fried Mee 26 · Guaraná Fantástica 20 · Chang 17.

Candidatos a liquidación. ✅

---

## SQL de confianza cargado (7)

1. Productos que hay que reponer · 2. Falsos positivos de reposición ·
3. Nivel de inventario vigente vs stock muerto · 4. Quiebres de stock ·
5. Inventario valorizado a precio de lista por categoría · 6. Cobertura en días ·
7. Descontinuados con stock

⚠️ **`example_question_sqls` no tiene campo de descripción** — la API rechaza `content` con
*Unknown field*. La descripción de cada consulta va como comentario `--` al tope del SQL.

⚠️ **Los `id` del proto deben ser UUID de 32 hex en minúscula y sin guiones**; `sq-01` es
rechazado. En el script se derivan por hash del contenido para que sean estables.
