# Banco de preguntas válidas — webinar Genie

Todas las preguntas ejecutadas contra los 4 spaces, con **la respuesta textual que dieron** y
su estado de verificación. Sirve para elegir qué sacar en vivo sabiendo de antemano qué va a
contestar el Genie.

- **Plataforma:** Databricks on AWS · workspace `dbc-fba20ab2-d1fc` · perfil `-p webinar-aws`
- **Fecha de validación:** 14-ago-2026 · **corte de datos:** 2026-05-06
- ✅ = ejecutada y respuesta transcrita · ⚪ = cargada como sugerida pero **no ejecutada**
- **21 preguntas ejecutadas · no queda ninguna ⚪** (las 4 del Radar se cerraron el 14-ago).

| space | id | catálogo |
|---|---|---|
| Ventas Neptuno (CRUDO) | `01f1979ee629133bb42428d55e433cff` | `neptuno` |
| Ventas Neptuno AI (CURADO) | `01f197a3c2c51e0493319fcefc5fb835` | `neptuno_ai` |
| Inventario Neptuno (CURADO) | `01f197a1f44d173a824fb4810124d4c6` | `neptuno_ai` |
| Radar Comercial (CURADO) | `01f197a566ab13499bbdfd31a9bb6e9e` | `neptuno_ai` |

> ⚠️ **Los importes cambian de centavos entre spaces.** El curado usa la función
> `venta_neta()` y cierra en `617.085,33` / `103.924,32`; el cálculo directo del crudo da
> `617.085,20` / `103.924,31`. Es redondeo de la función, no un error — pero si los mostrás
> lado a lado, alguien lo va a notar. Mejor mencionarlo vos primero.

---

# 1 · El A/B — la columna vertebral del webinar

Misma pregunta, dos spaces abiertos al lado. **No hace falta curar en vivo ni hacer rollback.**

### ✅ ¿Cuál es el margen de la categoría Bebidas? ⭐ EL DEMO 0

**CRUDO:**
> «El margen total de la categoría **Bebidas** es **267,868.18**. Este valor representa la suma
> de los ingresos netos (después de descuentos) generados por las ventas de productos en esta
> categoría.»

**CURADO:**
> «**No es posible calcular el margen ni la rentabilidad**, ya que el modelo no tiene costo de
> mercadería. Sin embargo, puedo mostrarte la venta neta de la categoría Bebidas. ¿Quieres ver
> la venta neta por año o en total?»

🚨 **Cambió respecto de julio.** Antes el crudo restaba precio de venta − precio de catálogo y
daba **−23.055,30 «pérdida»**. Ahora **no resta nada**: llama «margen» a la venta neta. Menos
dramático (no hay número negativo), pero la tesis se sostiene: **sin costos en el modelo,
afirma un margen con total seguridad en vez de decir que no puede.**

### ✅ ¿Cuántos clientes activos tenemos?
| CRUDO | CURADO |
|---|---|
| **89** — «según los datos actuales» | **87** — «clientes que realizaron al menos un pedido en los últimos 12 meses» |

El crudo cuenta a cualquiera que compró alguna vez. Definición inventada, número creíble.

### ✅ Compara las ventas de este año contra el año pasado
| CRUDO | CURADO |
|---|---|
| «2026: **440,623.87**, 2025: **617,085.20**. Esto muestra una **disminución**» | «2025: **617,085.33**; 2026 (**año parcial, solo hasta mayo**): **440,623.92**. **Los valores de 2026 no son comparables con 2025** porque solo incluyen parte del año» |

El crudo declara una caída del negocio comparando 5 meses contra 12.

### ✅ ¿Cuánto vendimos de la categoría Bebidas el año pasado?
- **CRUDO: 103,924.31** ✅ acierta
- **CURADO: 103,924.305** ✅ (vía `venta_neta()`)

Sirve para mostrar que **curar no rompe lo que ya salía bien**.

### ✅ ¿Cuál fue el ticket promedio el año pasado?
**CRUDO: 1512.46** ✅ acierta.

### ✅ ¿Cuántos productos tenemos a la venta?
**CRUDO: 67** ✅ acierta — filtró `Suspendido = 0` solo.

---

# 2 · Inventario — la trampa más cara

### ✅ ¿Qué productos tengo que reponer? ⭐ LA MÁS FUERTE

**CRUDO (space de ventas, tablas sin curar):**
> «Tienes **17 productos** activos que necesitan reposición… Algunos de los más urgentes son:
> **Gorgonzola Telino**: **0** en existencia, nivel de reposición **20**, **70 en pedido** ·
> Louisiana Hot Spiced Okra: 4 en existencia, nivel 20, **100 en pedido** · Mascarpone Fabioli:
> 9 en existencia, nivel 25, **40 en pedido**…»

**CURADO:**
> «Debes reponer los siguientes productos, ya que el stock disponible más lo que está en camino
> no alcanza el punto de reorden:
> · **Nord-Ost Matjeshering** (Pescados y Mariscos): stock 10, en camino 0, punto de reorden 15
> · **Outback Lager** (Bebidas): stock 15, en camino 10, punto de reorden 30
> Ambos con un faltante de 5 unidades.»

| | |
|---|---|
| Crudo | **17 productos** |
| Real | **2** |
| Falsos positivos | **16 → pediría 8× más mercadería** |

🔑 **El golpe de efecto:** el crudo **muestra el «70 en pedido» en su propia respuesta** sin
darse cuenta de que contradice su conclusión. La evidencia de su error está en su salida.

### ✅ ¿Cuál es mi nivel de inventario?
| CRUDO | CURADO |
|---|---|
| «**3119 unidades**… la suma de todas las unidades en existencia» | «vigente **2,962** · stock muerto **157** (descontinuados) · total bruto **3,119**» |

157 unidades de producto dado de baja contadas como inventario.

### ✅ ¿Qué productos están agotados?
> «**Gorgonzola Telino** (Lacteos) está agotado, pero tiene **70 unidades en camino** y su
> situación es **reposición en curso**. No es necesario reabastecer este artículo.»

📌 Hay **5 productos con existencia 0**, pero sólo **1 es vigente**; los otros 4 son
descontinuados y se filtran.

### ✅ ¿Cuántos días de cobertura tengo por producto?
> «**Gorgonzola Telino 0 días** · Sir Rodney's Scones **1,8** … Grandma's Boysenberry Spread
> **438** · Laughing Lumberjack Lager **292**. El rango va de 0 a 438 días.»

### ✅ ¿Cuánto vale mi inventario por categoría?
> «Pescados y Mariscos **13,010.35** · Condimentos **11,926.05** · Bebidas **11,365.25** ·
> Lácteos **11,271.20** · Repostería **10,392.20** … menor: Frutas y Verduras **2,363.75**.
> *Recuerda que esto no es costo ni valor contable, porque el modelo no incluye costos.*»

🔑 **La aclaración salió sola.** Es el mismo límite del Demo 0, pero acá lo dice **antes** de
que alguien caiga en la trampa.

### ✅ ¿Qué productos descontinuados siguen ocupando almacén?
> «**Chai** (Bebidas) **39 u** · Mishi Kobe Niku **29** · Rössle Sauerkraut **26** ·
> Singaporean Hokkien Fried Mee **26** · Guaraná Fantástica **20** · Chang **17**.»

---

# 3 · Radar comercial — el radar que se apaga solo

### ✅ ¿Qué clientes se están cayendo? ⭐
> «Comparando **enero-mayo 2026 vs enero-mayo 2025** (mismo rango de meses), hay **23 clientes**
> con caída en venta neta. Los más fuertes: **Simons bistro** (Dinamarca) de 11,188.40 a 232.09
> (**−97.9 %**) · **Wartian Herkku** (Finlandia) **−96.0 %** · **Seven Seas Imports** (Reino
> Unido) **−69.1 %** · **Furia Bacalhau** (Portugal) **−98.4 %** · **Blondesddsl père et fils**
> (Francia) **−81.0 %**»

| | |
|---|---|
| Comparando año vs año | **48 de 79 "caen"** |
| Mismo rango (ene-may) | **23** |
| Falsas alarmas | **~25 — más de la mitad del radar sería ruido** |

🔑 **El argumento:** un radar que dispara 48 alertas cuando hay 23 problemas reales **se apaga
solo** — el equipo deja de mirarlo a la segunda semana.

### ✅ ¿Quién es mi mejor vendedor?
> «Tu mejor vendedor **por venta neta** es **Margaret Peacock**… ocupa el primer lugar usando
> específicamente el criterio de **venta neta**. ¿Quieres que te muestre el mejor vendedor según
> **ticket promedio** o **número de clientes atendidos** en lugar de venta neta?»

| Criterio | Gana (2025) |
|---|---|
| Venta neta | **Margaret Peacock** (128.810) |
| Ticket promedio | **Andrew Fuller** (1.718) — Margaret cae al 5.º |
| Clientes atendidos | Margaret Peacock (57) |

### ✅ ¿Qué clientes dejaron de comprar? *(ejecutada 14-ago)*
> «**Centro comercial Moctezuma** (México): última compra **18-jul-2024**, 1 pedido histórico,
> **657 días** sin comprar — perdido según inactividad > 12 meses **respecto al corte de datos**.»

📌 El SQL usa `MAX(FechaPedido)` como corte, no `CURRENT_DATE`. Es la trampa #3 curada, visible.

### ✅ ¿Cuánto depende el negocio de mis 10 mejores clientes? *(ejecutada 14-ago)*
> «En 2025 los 10 mejores clientes aportaron el **46,50 %** de la venta neta total. Alta
> concentración de cartera: casi la mitad de los ingresos dependen de ese grupo reducido.»

📌 Calculado con la UC Function `venta_neta()` (capa 5).

### ✅ ¿Qué categorías están cayendo este año? ⭐ *(ejecutada 14-ago)*
> «**Ninguna categoría cae** en 2026 (ene-may) frente al mismo periodo de 2025; todas crecen.
> Condimentos +36,4 % … Pescados y Mariscos +158,5 %.»

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

🔑 **Buen momento de escena:** la pregunta **presupone** una caída y el space contesta que no
hay ninguna, en vez de fabricar un ranking de «las que menos crecen». Mismo comportamiento que
el A/B de ventas, pero sobre un sesgo que trae el usuario en la pregunta.
⚠️ Contraejemplo perfecto del año parcial: comparando 2026-completo vs 2025-completo **todas
caerían**. La comparación justa invierte el veredicto entero.

### ✅ ¿Qué transportista se atrasa más? *(ejecutada 14-ago)*
> «**Paquetes Unidos**, con **5,1 %** de pedidos con retraso (**16 de 315** envíos).»

📌 Devuelve el denominador junto al porcentaje.

**Estado del Radar: las 6 preguntas sugeridas están verificadas por ejecución real. No queda
ninguna ⚪.**

---

# 4 · Cifras de referencia (verificadas por SQL directo)

| Dato | Valor |
|---|---|
| Pedidos · líneas | **830** · **2.155** |
| Venta neta 2025 | **617.085,20** |
| Bebidas 2025 | **103.924,31** |
| Productos | 77 (**67 vigentes**, 10 descontinuados) |
| Sin stock | 5 (**sólo 1 vigente**) |
| Bajo punto de reorden | 18 · con reposición en curso 17 |
| A reponer de verdad | **2** |
| Inventario | **2.962** vigente · 157 muerto · 3.119 bruto |
| Vendedores · clientes · transportistas | 9 · 89 · 3 |
| Rango de datos | 2024-07-04 → **2026-05-06** (100 días de desfase con hoy) |
| Clientes en ambos años | 79 · «caen» 48 · caen de verdad 22-23 |
| Venta por categoría (histórico) | Bebidas 267.868,18 · Lácteos 234.507,29 · Repostería 167.357,22 · Carnes 163.022,36 · Pescados 131.261,74 · Condimentos 106.047,09 · Frutas 99.984,58 · Granos 95.744,59 |

---

# 5 · Cómo reproducir todo esto

```bash
export GENIE_PROFILE=webinar-aws GENIE_WAREHOUSE=2b2c1ffece1d2787
cd ~/clawd/webinar-genie

python3 bootstrap.py          # neptuno crudo: 8 tablas + verificación de cifras
python3 montar_ai.py          # neptuno_ai: clon + capas SQL (1, 5, 6)
python3 dbsql.py < capas-inventario.sql   # capa 1 de inventario, SÓLO en neptuno_ai
python3 ventas_ai_space.py    # space curado de ventas
python3 inventario_space.py   # space de inventario
python3 radar_space.py        # space de radar comercial
```

Los tres scripts de space aceptan `--update <space_id>` para re-aplicar la curación sin
duplicar (los ids se derivan por hash del contenido).

🚨 `python3 dbsql.py < capas.sql` cierra con un `PARSE_SYNTAX_ERROR` **inofensivo**: el runner
intenta ejecutar el bloque final de comentarios del rollback. Las capas se aplican todas.
