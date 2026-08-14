# Genie Space «Radar Comercial Neptuno» — CURADO · preguntas validadas

**Space:** `01f197a566ab13499bbdfd31a9bb6e9e` · **Catálogo:** `neptuno_ai`
→ https://dbc-fba20ab2-d1fc.cloud.databricks.com/genie/rooms/01f197a566ab13499bbdfd31a9bb6e9e

Creado con `radar_space.py` (`--update <space_id>` re-aplica la curación sin duplicar).

**Por qué este caso:** «Radar comercial» es uno de los 11 tipos de Genie con demanda verificada
— **Casas Bahia** bajó de 5-6 h a 2 min, **The AA**.

**Tablas:** `pedidos`, `detalles_pedidos`, `clientes`, `empleados`, `productos`, `categorias`,
`transportistas`.

---

## Las trampas que cura (medidas el 14-ago-2026)

### 1. El año parcial dispara falsas alarmas — la más fuerte

Los datos terminan el **2026-05-06**: 2026 tiene 5 meses y 2025 tiene 12.

| «¿Qué clientes están cayendo?» | |
|---|---|
| Comparando 2026 completo vs 2025 completo | **48 de 79 "caen"** |
| Comparando el mismo rango (ene-may) | **23** |
| **Falsas alarmas** | **~25 — más de la mitad del radar sería ruido** |

Un radar que dispara 48 alertas cuando hay ~23 problemas reales **se apaga solo**: el equipo
comercial deja de mirarlo. No es un error de cálculo, es un error de comparación.

### 2. «El mejor» exige un criterio, y nadie lo declara

| Criterio | Gana |
|---|---|
| Venta neta | **Margaret Peacock** (128.810 en 2025) |
| Ticket promedio | **Andrew Fuller** (1.718) — Margaret cae al 5.º puesto |
| Clientes atendidos | Margaret Peacock (57) |

Sin declarar el criterio, la respuesta es arbitraria y suena a verdad.

### 3. El corte de datos no es hoy

**100 días de desfase** entre el último pedido (2026-05-06) y la fecha actual. Medir «últimos
12 meses» contra `CURRENT_DATE` corre la ventana y hace desaparecer actividad real. Todas las
ventanas móviles se calculan contra el **máximo `FechaPedido` de la base**.

---

## Respuestas verificadas

### ¿Qué clientes se están cayendo?
> «Comparando **enero-mayo 2026 vs enero-mayo 2025** (mismo rango de meses), hay **23 clientes**
> con caída en venta neta. Los casos más fuertes: **Simons bistro** (Dinamarca) de 11.188,40 a
> 232,09 (**−97,9 %**) · **Wartian Herkku** (Finlandia) −96,0 % · **Seven Seas Imports** (Reino
> Unido) −69,1 % · **Furia Bacalhau** (Portugal) −98,4 % · **Blondesddsl père et fils** −81,0 %»

✅ Eligió solo el mismo rango de meses y **lo dijo en la respuesta**. 23, no 48.

### ¿Quién es mi mejor vendedor?
> «Tu mejor vendedor **por venta neta** es **Margaret Peacock**… En este resultado ocupa el
> primer lugar usando específicamente el criterio de **venta neta**.
> ¿Quieres que te muestre el mejor vendedor según **ticket promedio** o **número de clientes
> atendidos** en lugar de venta neta?»

✅ Declara el criterio **y** ofrece los otros dos, en vez de dar un ganador a secas.
📌 Ese importe es el histórico completo: si querés 2025, hay que pedir el año — el SQL de
confianza sí lo filtra.

---

### ¿Qué clientes dejaron de comprar? ✅ *(verificada 14-ago)*
> «**Centro comercial Moctezuma** (México) dejó de comprar: última compra **18-jul-2024**,
> 1 pedido histórico, **657 días** sin comprar — cliente perdido según la definición de
> inactividad > 12 meses **respecto al corte de datos**.»

✅ El SQL calcula el corte con `MAX(FechaPedido)`, no con `CURRENT_DATE` — la trampa #3 curada.

### ¿Cuánto depende el negocio de mis 10 mejores clientes? ✅ *(verificada 14-ago)*
> «En 2025 los 10 mejores clientes aportaron el **46,50 %** de la venta neta total. Alta
> concentración de cartera: casi la mitad de los ingresos dependen de ese grupo reducido.»

✅ Usa la UC Function `venta_neta()` (capa 5), no `PrecioUnidad*Cantidad`.

### ¿Qué categorías están cayendo este año? ✅ *(verificada 14-ago)*
> «**Ninguna categoría cae** en 2026 (enero-mayo) frente al mismo periodo de 2025; todas
> crecen. Condimentos +36,4 % … Pescados y Mariscos +158,5 %.»

| categoría | ene-may 2025 | ene-may 2026 | var. |
|---|---|---|---|
| Condimentos | 24.023,50 | 32.778,13 | +36,4 % |
| Granos y Cereales | 21.220,75 | 29.364,85 | +38,4 % |
| Reposteria | 38.545,36 | 55.013,93 | +42,7 % |
| Frutas y Verduras | 18.054,78 | 31.158,03 | +72,6 % |
| Lacteos | 40.591,32 | 78.139,21 | +92,5 % |
| Carnes y Aves | 27.411,30 | 53.233,60 | +94,2 % |
| Bebidas | 57.883,48 | 116.024,88 | +100,4 % |
| Pescados y Mariscos | 17.372,70 | 44.911,29 | +158,5 % |

🔑 **Vale como momento de escena:** la pregunta presupone una caída y el space **contesta que
no hay ninguna** en vez de fabricar un ranking de «las que menos crecen». Es el mismo
comportamiento que el A/B de ventas («no se puede calcular el margen»), pero sobre un caso
donde el usuario ya trae el sesgo en la pregunta.
⚠️ Y es exactamente el contraejemplo del año parcial: comparado 2026-completo vs 2025-completo
todas «caerían». Aquí la comparación justa invierte el veredicto entero.

### ¿Qué transportista se atrasa más? ✅ *(verificada 14-ago)*
> «**Paquetes Unidos**, con **5,1 %** de pedidos enviados con retraso (**16 de 315** envíos).»

📌 Da el denominador junto al porcentaje — un 5,1 % sobre 315 envíos se puede juzgar; el
porcentaje solo, no.

---

**Estado: las 6 preguntas sugeridas están verificadas por ejecución real (14-ago-2026).**
Ya no queda ninguna ⚪.

## SQL de confianza cargado (7)

1. Clientes que caen — comparación justa · 2. Clientes en riesgo y perdidos (medidos contra el
corte) · 3. Ranking de vendedores por los tres criterios · 4. Concentración de cartera ·
5. Cumplimiento de entrega por transportista · 6. Evolución mensual marcando el año parcial ·
7. Categorías que se están cayendo

## Preguntas sugeridas

1. ¿Qué clientes se están cayendo? · 2. ¿Qué clientes dejaron de comprar? ·
3. ¿Quién es mi mejor vendedor? · 4. ¿Cuánto depende el negocio de mis 10 mejores clientes? ·
5. ¿Qué categorías están cayendo este año? · 6. ¿Qué transportista se atrasa más?
