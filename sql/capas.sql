-- ═══════════════════════════════════════════════════════════════════════
-- WEBINAR «Databricks Genie en producción» — las 6 capas, en vivo
-- Dataset: neptuno.ventas (sandbox v5)
--
-- Las tablas nacen DESNUDAS a propósito. Cada bloque de abajo se ejecuta
-- EN VIVO, y después de cada uno se repite la MISMA pregunta en el Genie:
--
--     «¿Cuánto vendimos de la categoría Bebidas el año pasado?»
--
--   respuesta cruda   → US$ 108.545,00  (sin descuento, por FechaEnvio)
--   respuesta correcta → US$ 103.924,31  (venta neta, por FechaPedido)
--   diferencia: US$ 4.620,70 — solo 4,4%. Por eso nadie lo detecta.
-- ═══════════════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────────────
-- CAPA 1 · METADATOS EN UNITY CATALOG
-- Lo más barato que existe, y lo que todos se saltan.
-- ─────────────────────────────────────────────────────────────────────

COMMENT ON TABLE neptuno.ventas.detalles_pedidos IS
'Hecho a nivel de línea: una fila = un producto dentro de un pedido. El ingreso de una línea NO es PrecioUnidad*Cantidad: hay que aplicar el Descuento. PrecioUnidad aquí es el precio HISTÓRICO al que se vendió, que puede diferir del precio actual en la tabla productos.';

COMMENT ON TABLE neptuno.ventas.pedidos IS
'Cabecera de pedido: una fila = un pedido. Para analizar ventas se usa FechaPedido (cuándo se vendió), no FechaEnvio ni FechaEntrega. Cargo es el costo de flete del pedido: NO es ingreso y no se suma a las ventas.';

COMMENT ON TABLE neptuno.ventas.productos IS
'Catálogo de productos. PrecioUnidad es el precio de lista ACTUAL, no el precio al que se vendió históricamente — para calcular ventas se usa el PrecioUnidad de detalles_pedidos.';

COMMENT ON TABLE neptuno.ventas.categorias IS 'Categorías de producto (8): Bebidas, Condimentos, Reposteria, Lacteos, Granos y Cereales, Carnes y Aves, Frutas y Verduras, Pescados y Mariscos.';
COMMENT ON TABLE neptuno.ventas.clientes IS 'Clientes (empresas) de Neptuno. IdCliente es un código alfanumérico de 5 letras, no un número.';
COMMENT ON TABLE neptuno.ventas.empleados IS 'Fuerza de ventas y administración. JefeId apunta al IdEmpleado del jefe (jerarquía dentro de la misma tabla).';
COMMENT ON TABLE neptuno.ventas.proveedores IS 'Proveedores a los que Neptuno compra los productos que importa.';
COMMENT ON TABLE neptuno.ventas.transportistas IS 'Empresas de transporte que entregan los pedidos.';

-- las columnas que causan el error
ALTER TABLE neptuno.ventas.detalles_pedidos ALTER COLUMN Descuento COMMENT
'Descuento aplicado a la línea, expresado de 0 a 1 (0.15 = 15%). Debe restarse SIEMPRE para obtener el ingreso real: PrecioUnidad * Cantidad * (1 - Descuento).';
ALTER TABLE neptuno.ventas.detalles_pedidos ALTER COLUMN PrecioUnidad COMMENT
'Precio unitario histórico al que se vendió el producto en este pedido, en USD. Este es el precio que se usa para calcular ventas.';
ALTER TABLE neptuno.ventas.detalles_pedidos ALTER COLUMN Cantidad COMMENT 'Unidades del producto vendidas en esta línea.';

ALTER TABLE neptuno.ventas.pedidos ALTER COLUMN FechaPedido COMMENT
'Fecha en que se realizó el pedido. Es la fecha de referencia para analizar ventas por periodo.';
ALTER TABLE neptuno.ventas.pedidos ALTER COLUMN FechaEnvio COMMENT
'Fecha en que el pedido salió del almacén. NULL si todavía no se ha enviado. No usar para analizar ventas.';
ALTER TABLE neptuno.ventas.pedidos ALTER COLUMN FechaEntrega COMMENT
'Fecha comprometida de entrega al cliente. Sirve para medir cumplimiento, no ventas.';
ALTER TABLE neptuno.ventas.pedidos ALTER COLUMN Cargo COMMENT
'Costo de flete del pedido en USD. Es un COSTO, no un ingreso: nunca se suma a las ventas.';

ALTER TABLE neptuno.ventas.productos ALTER COLUMN PrecioUnidad COMMENT
'Precio de lista actual del producto en USD. NO es un costo: el modelo no tiene costo de mercadería, por lo que NO se puede calcular margen ni utilidad. No usar para ventas históricas (para eso está detalles_pedidos.PrecioUnidad).';
ALTER TABLE neptuno.ventas.productos ALTER COLUMN Suspendido COMMENT
'1 = producto descontinuado (ya no se vende), 0 = activo. Al preguntar por productos vigentes hay que filtrar Suspendido = 0.';
ALTER TABLE neptuno.ventas.productos ALTER COLUMN UnidadesEnExistencia COMMENT 'Stock disponible en almacén.';

ALTER TABLE neptuno.ventas.clientes ALTER COLUMN NombreCompania COMMENT 'Razón social del cliente. Es el nombre por el que el negocio se refiere al cliente.';
ALTER TABLE neptuno.ventas.empleados ALTER COLUMN Cargo COMMENT 'Puesto del empleado, ej. Representante de Ventas, Gerente de Ventas.';


-- ─────────────────────────────────────────────────────────────────────
-- CAPA 5 · UC FUNCTION — la regla de negocio deja de ser improvisable
-- (se aplica después de las capas 2-4, que van en la UI del Genie space)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION neptuno.ventas.venta_neta(
  precio_unidad DECIMAL(10,2),
  cantidad      INT,
  descuento     DOUBLE
)
RETURNS DECIMAL(18,2)
COMMENT 'Ingreso neto de una línea de pedido en USD. Es la ÚNICA definición válida de venta: precio histórico * cantidad, menos el descuento aplicado. Usar siempre esta función para calcular ventas, facturación o ingresos.'
RETURN CAST(precio_unidad * cantidad * (1 - descuento) AS DECIMAL(18,2));

-- prueba: debe dar 103924.31
SELECT ROUND(SUM(neptuno.ventas.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta_bebidas_2025
FROM neptuno.ventas.detalles_pedidos d
JOIN neptuno.ventas.pedidos    p  ON p.IdPedido    = d.IdPedido
JOIN neptuno.ventas.productos  pr ON pr.IdProducto = d.IdProducto
JOIN neptuno.ventas.categorias c  ON c.IdCategoria = pr.IdCategoria
WHERE c.NombreCategoria = 'Bebidas' AND YEAR(p.FechaPedido) = 2025;


-- ─────────────────────────────────────────────────────────────────────
-- CAPA 6 · RELACIONES DECLARADAS — se acaban los JOIN inventados
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE neptuno.ventas.categorias     ALTER COLUMN IdCategoria     SET NOT NULL;
ALTER TABLE neptuno.ventas.clientes       ALTER COLUMN IdCliente       SET NOT NULL;
ALTER TABLE neptuno.ventas.empleados      ALTER COLUMN IdEmpleado      SET NOT NULL;
ALTER TABLE neptuno.ventas.productos      ALTER COLUMN IdProducto      SET NOT NULL;
ALTER TABLE neptuno.ventas.proveedores    ALTER COLUMN IdProveedor     SET NOT NULL;
ALTER TABLE neptuno.ventas.transportistas ALTER COLUMN IdTransportista SET NOT NULL;
ALTER TABLE neptuno.ventas.pedidos        ALTER COLUMN IdPedido        SET NOT NULL;
ALTER TABLE neptuno.ventas.detalles_pedidos ALTER COLUMN IdPedido      SET NOT NULL;
ALTER TABLE neptuno.ventas.detalles_pedidos ALTER COLUMN IdProducto    SET NOT NULL;

ALTER TABLE neptuno.ventas.categorias     ADD CONSTRAINT pk_categorias     PRIMARY KEY (IdCategoria);
ALTER TABLE neptuno.ventas.clientes       ADD CONSTRAINT pk_clientes       PRIMARY KEY (IdCliente);
ALTER TABLE neptuno.ventas.empleados      ADD CONSTRAINT pk_empleados      PRIMARY KEY (IdEmpleado);
ALTER TABLE neptuno.ventas.productos      ADD CONSTRAINT pk_productos      PRIMARY KEY (IdProducto);
ALTER TABLE neptuno.ventas.proveedores    ADD CONSTRAINT pk_proveedores    PRIMARY KEY (IdProveedor);
ALTER TABLE neptuno.ventas.transportistas ADD CONSTRAINT pk_transportistas PRIMARY KEY (IdTransportista);
ALTER TABLE neptuno.ventas.pedidos        ADD CONSTRAINT pk_pedidos        PRIMARY KEY (IdPedido);
-- el hecho: clave compuesta, así queda explícito el grano
ALTER TABLE neptuno.ventas.detalles_pedidos ADD CONSTRAINT pk_detalles PRIMARY KEY (IdPedido, IdProducto);

ALTER TABLE neptuno.ventas.productos ADD CONSTRAINT fk_prod_categoria
  FOREIGN KEY (IdCategoria) REFERENCES neptuno.ventas.categorias;
ALTER TABLE neptuno.ventas.productos ADD CONSTRAINT fk_prod_proveedor
  FOREIGN KEY (IdProveedor) REFERENCES neptuno.ventas.proveedores;
ALTER TABLE neptuno.ventas.pedidos ADD CONSTRAINT fk_ped_cliente
  FOREIGN KEY (IdCliente) REFERENCES neptuno.ventas.clientes;
ALTER TABLE neptuno.ventas.pedidos ADD CONSTRAINT fk_ped_empleado
  FOREIGN KEY (IdEmpleado) REFERENCES neptuno.ventas.empleados;
ALTER TABLE neptuno.ventas.pedidos ADD CONSTRAINT fk_ped_transportista
  FOREIGN KEY (IdTransportista) REFERENCES neptuno.ventas.transportistas;
ALTER TABLE neptuno.ventas.detalles_pedidos ADD CONSTRAINT fk_det_pedido
  FOREIGN KEY (IdPedido) REFERENCES neptuno.ventas.pedidos;
ALTER TABLE neptuno.ventas.detalles_pedidos ADD CONSTRAINT fk_det_producto
  FOREIGN KEY (IdProducto) REFERENCES neptuno.ventas.productos;


-- ═══════════════════════════════════════════════════════════════════════
-- ROLLBACK — para volver al estado crudo y poder ensayar de nuevo
-- ═══════════════════════════════════════════════════════════════════════
-- ALTER TABLE neptuno.ventas.detalles_pedidos DROP CONSTRAINT fk_det_producto;
-- ALTER TABLE neptuno.ventas.detalles_pedidos DROP CONSTRAINT fk_det_pedido;
-- ALTER TABLE neptuno.ventas.pedidos DROP CONSTRAINT fk_ped_transportista;
-- ALTER TABLE neptuno.ventas.pedidos DROP CONSTRAINT fk_ped_empleado;
-- ALTER TABLE neptuno.ventas.pedidos DROP CONSTRAINT fk_ped_cliente;
-- ALTER TABLE neptuno.ventas.productos DROP CONSTRAINT fk_prod_proveedor;
-- ALTER TABLE neptuno.ventas.productos DROP CONSTRAINT fk_prod_categoria;
-- ALTER TABLE neptuno.ventas.detalles_pedidos DROP CONSTRAINT pk_detalles;
-- ... (idem para el resto de PKs)
-- DROP FUNCTION IF EXISTS neptuno.ventas.venta_neta;
-- COMMENT ON TABLE neptuno.ventas.detalles_pedidos IS NULL;  -- idem resto
-- o directamente: python3 crear_tablas.py  (recrea las tablas desnudas)
