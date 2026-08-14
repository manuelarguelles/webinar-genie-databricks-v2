# Genie Space «Ventas Neptuno» — contenido para pegar en la UI

Las capas 1, 5 y 6 son SQL (`capas.sql`). Las capas **2, 3 y 4** viven dentro del Genie space
y se pegan desde su UI. Esto es el texto listo para copiar, en el orden del webinar.

- **Space:** Ventas Neptuno
- **Tablas:** las 8 de `neptuno.ventas`
- **Warehouse:** Serverless Starter Warehouse (`301ae960fc896653`)
- **Pregunta ancla** (se repite después de cada capa):
  *«¿Cuánto vendimos de la categoría Bebidas el año pasado?»*
  → crudo `US$ 108.545,00` · correcto **`US$ 103.924,31`**

---

## CAPA 2 · Instrucciones del space

> Pegar en **Instructions → General instructions**.

```text
Neptuno es una empresa de importación y distribución mayorista de alimentos gourmet.
Vende a clientes empresa (restaurantes, tiendas y distribuidores) en varios países.
Responde siempre en español.

DEFINICIONES DE NEGOCIO
- "Ventas", "facturación", "ingresos" y "revenue" son la MISMA métrica: la venta neta.
- La venta neta de una línea es PrecioUnidad * Cantidad * (1 - Descuento), usando el
  PrecioUnidad de detalles_pedidos (precio histórico), nunca el de productos.
- El Cargo de un pedido es flete: es un costo, NUNCA se suma a las ventas.
- No tenemos costo de mercadería: no calcules margen ni utilidad. Si lo piden, acláralo.

FECHAS
- Por defecto usa FechaPedido. FechaEnvio y FechaEntrega solo si lo piden explícitamente.
- Los datos van de julio 2024 a mayo 2026. "El año pasado" = 2025 (último año completo).
- 2026 es un año parcial: al compararlo con 2025 advierte que no es comparable.

MONEDA Y FORMATO
- Todos los importes están en USD. Redondea a 2 decimales.
- Cuando devuelvas un ranking, ordena de mayor a menor y limita a 10 salvo que pidan más.
```

---

## CAPA 3 · SQL curado (trusted queries)

> Pegar en **Instructions → SQL queries**. Cada una con su nombre y descripción:
> Genie las usa como ejemplo canónico y generaliza el patrón.

### 1. Venta neta por categoría y año
*Descripción: cuánto se vendió (venta neta) por categoría de producto en cada año. Es la forma correcta de calcular ventas: aplica el descuento y usa FechaPedido.*
```sql
SELECT c.NombreCategoria,
       YEAR(p.FechaPedido) AS anio,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * (1 - d.Descuento)), 2) AS venta_neta
FROM neptuno.ventas.detalles_pedidos d
JOIN neptuno.ventas.pedidos    p  ON p.IdPedido    = d.IdPedido
JOIN neptuno.ventas.productos  pr ON pr.IdProducto = d.IdProducto
JOIN neptuno.ventas.categorias c  ON c.IdCategoria = pr.IdCategoria
GROUP BY c.NombreCategoria, YEAR(p.FechaPedido)
ORDER BY anio, venta_neta DESC
```

### 2. Top clientes por venta neta
*Descripción: ranking de clientes por cuánto compraron (venta neta) en un periodo.*
```sql
SELECT cl.NombreCompania AS cliente,
       cl.Pais,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * (1 - d.Descuento)), 2) AS venta_neta,
       COUNT(DISTINCT p.IdPedido) AS pedidos
FROM neptuno.ventas.detalles_pedidos d
JOIN neptuno.ventas.pedidos  p  ON p.IdPedido  = d.IdPedido
JOIN neptuno.ventas.clientes cl ON cl.IdCliente = p.IdCliente
WHERE YEAR(p.FechaPedido) = 2025
GROUP BY cl.NombreCompania, cl.Pais
ORDER BY venta_neta DESC
LIMIT 10
```

### 3. Venta neta por vendedor
*Descripción: desempeño de la fuerza de ventas — cuánto vendió cada empleado.*
```sql
SELECT CONCAT(e.Nombre, ' ', e.Apellidos) AS vendedor,
       e.Cargo,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * (1 - d.Descuento)), 2) AS venta_neta
FROM neptuno.ventas.detalles_pedidos d
JOIN neptuno.ventas.pedidos   p ON p.IdPedido   = d.IdPedido
JOIN neptuno.ventas.empleados e ON e.IdEmpleado = p.IdEmpleado
WHERE YEAR(p.FechaPedido) = 2025
GROUP BY e.Nombre, e.Apellidos, e.Cargo
ORDER BY venta_neta DESC
```

### 4. Evolución mensual de ventas
*Descripción: serie mensual de venta neta, para ver tendencia.*
```sql
SELECT DATE_TRUNC('MONTH', p.FechaPedido) AS mes,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * (1 - d.Descuento)), 2) AS venta_neta,
       COUNT(DISTINCT p.IdPedido) AS pedidos
FROM neptuno.ventas.detalles_pedidos d
JOIN neptuno.ventas.pedidos p ON p.IdPedido = d.IdPedido
GROUP BY DATE_TRUNC('MONTH', p.FechaPedido)
ORDER BY mes
```

### 5. Impacto del descuento
*Descripción: cuánto dinero se deja en descuentos — la diferencia entre venta bruta y neta.*
```sql
SELECT YEAR(p.FechaPedido) AS anio,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad), 2) AS venta_bruta,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * (1 - d.Descuento)), 2) AS venta_neta,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * d.Descuento), 2) AS descuento_otorgado
FROM neptuno.ventas.detalles_pedidos d
JOIN neptuno.ventas.pedidos p ON p.IdPedido = d.IdPedido
GROUP BY YEAR(p.FechaPedido)
ORDER BY anio
```

### 6. Pedidos con entrega atrasada
*Descripción: pedidos que se enviaron después de la fecha comprometida de entrega.*
```sql
SELECT p.IdPedido, cl.NombreCompania AS cliente,
       p.FechaPedido, p.FechaEntrega, p.FechaEnvio,
       DATEDIFF(p.FechaEnvio, p.FechaEntrega) AS dias_atraso
FROM neptuno.ventas.pedidos p
JOIN neptuno.ventas.clientes cl ON cl.IdCliente = p.IdCliente
WHERE p.FechaEnvio > p.FechaEntrega
ORDER BY dias_atraso DESC
```

---

## CAPA 4 · Sinónimos y conocimiento semántico

> Pegar como instrucciones adicionales (o con **Add instruction** por columna).

```text
VOCABULARIO DEL NEGOCIO
- venta / ventas / facturación / ingresos / revenue / vendimos → venta neta
- cliente / cuenta / razón social / compañía → clientes.NombreCompania
- vendedor / comercial / asesor / representante → empleados (nombre + apellidos)
- producto / artículo / ítem / SKU → productos.NombreProducto
- rubro / línea / familia de producto → categorias.NombreCategoria
- flete / envío / transporte (costo) → pedidos.Cargo
- transportista / courier / operador logístico → transportistas.NombreCompania
- proveedor → proveedores.NombreCompania

DEFINICIONES
- Cliente activo: cliente con al menos un pedido en los últimos 12 meses.
- Producto vigente: productos.Suspendido = 0. Los suspendidos ya no se venden.
- Ticket promedio: venta neta total dividida entre número de pedidos distintos.
- Un "pedido" es una fila de pedidos; una "línea" es una fila de detalles_pedidos.

VALORES REALES (para que los filtros no fallen)
- Categorías: Bebidas, Condimentos, Reposteria, Lacteos, Granos y Cereales,
  Carnes y Aves, Frutas y Verduras, Pescados y Mariscos.
- Los países están en español: Estados Unidos, Reino Unido, Alemania, Francia,
  España, Brasil, Mexico, Canada, Italia, Suecia, Venezuela, Argentina, Suiza...
- Transportistas: Expreso Veloz, Paquetes Unidos, Envios Federales.
```
