# Common questions del space CURADO — validadas por API (23-jul · re-validadas 14-ago)

> **14-ago-2026 · plataforma AWS.** Los dos spaces existen a la vez, así que el A/B es lado a
> lado y **no hace falta rollback**:
> **crudo** `01f1979ee629133bb42428d55e433cff` (`neptuno`) ·
> **curado** `01f197a3c2c51e0493319fcefc5fb835` (`neptuno_ai`).
> Las 3 preguntas del A/B **reproducen la tabla de julio**: el margen se rechaza con la
> contraoferta de venta neta, clientes activos da **87**, y la comparación interanual **advierte**
> que 2026 es parcial. Ojo: por la función `venta_neta()` los importes cierran en `617.085,33`
> y `103.924,32` (vs `617.085,20` / `103.924,31` del cálculo directo) — es redondeo, no un error.

Pegar una a una con el botón ➕ en Configure → About → Common questions.

1. ¿Cuál es el margen de la categoría Bebidas?
2. ¿Cuántos clientes activos tenemos?
3. Compara las ventas de este año contra el año pasado
4. ¿Cuánto vendimos de la categoría Bebidas el año pasado?
5. ¿Cuál fue el ticket promedio el año pasado?
6. ¿Cuántos productos tenemos a la venta?

## Qué responde cada una (A/B verificado)

| # | CRUDO (mal) | CURADO (bien) |
|---|---|---|
| 1 | −23.055,30 «pérdida» | «No es posible calcular el margen… ¿quieres la venta neta?» |
| 2 | 89 (alguna vez compró) | 87 (pedido en los últimos 12 meses) |
| 3 | 2026: 440.623 vs 2025: 617.085 sin avisar | Pregunta si comparar año completo o solo hasta mayo |
| 4 | 103.924,31 (acierta) | 103.924,32 vía venta_neta() |
| 5 | 1.512,46 (acierta) | 1.512,46 vía venta_neta() + try_divide |
| 6 | 67 (acierta) | 67 «productos vigentes» |

Las 3 primeras son las del A/B. Las 3 últimas muestran que el curado no empeora
lo que ya salía bien, y que ahora todo pasa por la función gobernada.
