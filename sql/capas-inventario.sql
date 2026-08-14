-- ═══════════════════════════════════════════════════════════════════════
-- CAPA 1 del caso INVENTARIO — sólo para el catálogo CURADO (neptuno_ai)
--
-- capas.sql documenta el modelo desde la óptica de VENTAS y deja sin comentar
-- las dos columnas de las que depende la reposición. Este archivo cierra ese
-- hueco.
--
-- 🚨 EJECUTAR SÓLO CONTRA neptuno_ai. En `neptuno` (crudo) arruinaría el Demo 0
--    del space «Ventas Neptuno», que comparte esas tablas.
--
-- La trampa que cura: «¿qué productos tengo que reponer?»
--     sin curar → 17 productos (16 son falsos positivos)
--     curado    → 2 productos
--   porque UnidadesEnPedido es mercadería YA pedida que todavía no llegó.
-- ═══════════════════════════════════════════════════════════════════════

ALTER TABLE neptuno_ai.ventas.productos ALTER COLUMN UnidadesEnPedido COMMENT
'Unidades YA PEDIDAS al proveedor que todavía no llegaron (mercadería en tránsito). Para decidir una reposición hay que SUMARLAS al stock: un producto con 0 en existencia pero 70 en pedido NO se vuelve a comprar, ya está resuelto. Ignorar esta columna genera órdenes de compra duplicadas.';

ALTER TABLE neptuno_ai.ventas.productos ALTER COLUMN NivelNuevoPedido COMMENT
'Punto de reorden: nivel de stock por debajo del cual hay que reponer. La comparación correcta es (UnidadesEnExistencia + UnidadesEnPedido) <= NivelNuevoPedido, nunca sólo contra UnidadesEnExistencia. Si vale 0, el producto no se repone automáticamente.';

ALTER TABLE neptuno_ai.ventas.productos ALTER COLUMN UnidadesEnExistencia COMMENT
'Stock físico disponible hoy en almacén. No incluye lo que viene en camino (eso es UnidadesEnPedido). Un producto vigente con 0 acá está en quiebre de stock.';

ALTER TABLE neptuno_ai.ventas.productos ALTER COLUMN NombreProducto COMMENT
'Nombre comercial del producto (SKU). Es el nombre por el que el negocio se refiere al artículo.';

ALTER TABLE neptuno_ai.ventas.productos ALTER COLUMN CantidadPorUnidad COMMENT
'Formato de venta en texto libre (ej. "10 cajas x 20 bolsas"). Es descriptivo: NO sirve para calcular unidades ni convertir cantidades.';
