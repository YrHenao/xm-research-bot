# XM Research Bot — MT5 Demo Research

Bot modular en Python para investigar estrategias sobre Bitcoin/USD y oro con entradas M1, backtesting reproducible y herramientas de diagnóstico de MetaTrader 5 **exclusivamente en cuenta demo**.

> Estado actual: investigación/simulación. No hay evidencia de rentabilidad. La ejecución de órdenes está bloqueada por diseño en esta versión.

## Qué incluye

- Validación estricta de velas M1 cerradas.
- Seis detectores técnicos: soportes/resistencias, tendencia, Fibonacci, tres líneas, triángulos y Hombro-Cabeza-Hombro.
- Filtros de tendencia M15/H1/H4.
- Filtro de noticias point-in-time con cobertura explícita, conservado en el código pero desactivado temporalmente durante la fase actual de investigación.
- Gestión de riesgo y simulador de cartera.
- Replay y evaluación temporal 70/30.
- Adaptador MT5 limitado a cuentas demo.
- Descubrimiento de nombres reales de símbolos del broker.
- Inspección de especificaciones de contratos.
- Exportación de M1 cerradas desde MT5 para investigación offline.
- Suite de pruebas automatizadas.

## Seguridad

El proyecto está pensado para investigación y paper/demo trading. `MT5Adapter.account()` rechaza cuentas reales o desconocidas. La versión actual no expone un comando para enviar órdenes y `execute()` devuelve únicamente una solicitud simulada.

No introduzca credenciales en el repositorio.

## Requisitos

Python 3.11 o posterior. El núcleo utiliza solo la biblioteca estándar. La integración MT5 es opcional y requiere Windows con MetaTrader 5 instalado.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para instalar el adaptador de MetaTrader 5:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[mt5]"
```

## Prueba rápida sin MT5

Generar 1.200 velas sintéticas:

```powershell
.\.venv\Scripts\python.exe -m bot synthetic --bars 1200 --out synthetic.csv
```

Replay:

```powershell
.\.venv\Scripts\python.exe -m bot replay --data gold=synthetic.csv --out report.json
```

Los datos sintéticos sirven para probar el software. Sus resultados no representan comportamiento ni rentabilidad de mercado.

## Diagnóstico MT5 demo

Con MetaTrader 5 abierto y una cuenta demo activa:

```powershell
.\.venv\Scripts\python.exe -m bot mt5-inspect --query gold --query bitcoin --out mt5-demo-report.json
```

El comando:

1. comprueba que la cuenta sea DEMO;
2. busca símbolos compatibles con oro y Bitcoin;
3. devuelve nombres exactos del broker;
4. inspecciona contrato, tick, volumen, spread y modos de ejecución;
5. no envía órdenes.

Para exportar velas M1 cerradas:

```powershell
.\.venv\Scripts\python.exe -m bot mt5-export --symbol XAUUSD --bars 7000 --out gold_m1.csv
```

Sustituya `XAUUSD` por el nombre exacto encontrado con `mt5-inspect`.

## Datos offline

Cada CSV debe contener:

```text
time,open,high,low,close,spread
```

`time` es la apertura UTC en segundos Unix y debe ser múltiplo de 60. OHLC representa precios bid de velas M1 ya cerradas. `spread` se expresa en unidades de precio.

Ejemplo:

```powershell
.\.venv\Scripts\python.exe -m bot replay --data gold=gold_m1.csv --out gold-replay.json
.\.venv\Scripts\python.exe -m bot evaluate --data gold=gold_m1.csv --out gold-evaluation.json
```

`replay` usa todo el histórico aportado en una sola simulación. `evaluate` divide 70/30 por tiempo y compara la estrategia completa, cada detector aislado y la retirada de cada detector. No ajusta automáticamente parámetros.

## Riesgo de simulación

La configuración de ejemplo usa:

- riesgo por operación: 0,25 %;
- pérdida diaria: 2 %;
- máximo de posiciones: 2;
- riesgo abierto conjunto: 0,5 %;
- reward/risk: 2:1.

Son parámetros de investigación, no recomendaciones financieras.

## Stop loss opcional en backtesting

`strategy.stop_loss_enabled` controla únicamente el cierre por stop en `replay` y
`evaluate`. El ejemplo usa `false` para la prueba sin stop loss. Use `true` para
reactivarlo; si se omite el campo, se conserva el comportamiento anterior con
stop activo. Solo se aceptan booleanos JSON (`true` / `false`).

Con `false`, cruzar el stop no cierra la posición; siguen activos los cierres
por target, timeout y fin de datos (`end`). Si una vela cruza stop y target,
se ejecuta el target. Con `true`, el stop conserva la prioridad anterior.
La distancia `stop_atr` y el nivel `stop` se conservan como referencias para
dimensionar lotes, calcular riesgo nominal y fijar el target 2:1. Estos cálculos
no cambian, pero sin ejecutar el stop ese riesgo nominal no limita la pérdida
realizada. Los filtros de riesgo siguen controlando nuevas entradas.

Esta opción no modifica el adaptador MT5 ni habilita trading real o `order_send`.
Para guardar la prueba sin sobrescribir la línea base:

```powershell
.\.venv\Scripts\python.exe -m bot replay --data gold=gold_m1.csv --out gold-replay-no-stop.json
```

## Noticias

El módulo de noticias sigue dentro del proyecto (`bot/news.py`) y `news.template.json` se conserva para una fase posterior. Durante la fase actual de investigación, `config.example.json` usa:

```json
"news": {"required": false, "path": null, "before": 1800, "after": 1800}
```

Esto permite estudiar el histórico completo sin bloquear señales por ausencia de un proveedor de noticias. Para reactivar el filtro más adelante, cambie `required` a `true` y configure un archivo histórico point-in-time verificable.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La suite cubre también stop activo/inactivo, target, timeout, fin de datos y validación de la opción. Consulte `VALIDACION.md` para el alcance y las limitaciones.

## Próximos pasos

1. Ejecutar `replay` con todo el histórico M1 disponible para obtener una primera línea base.
2. Revisar operaciones, bloqueos, P&L simulado, drawdown y detectores activados.
3. Ejecutar `evaluate` para comparar train/test y contribución de cada detector.
4. Añadir validación walk-forward y sensibilidad a costes.
5. Construir un dashboard de análisis separado del motor.
6. Reintegrar noticias históricas point-in-time en una fase posterior.
