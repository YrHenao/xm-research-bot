# XM Research Bot — MT5 Demo Research

Bot modular en Python para investigar estrategias sobre Bitcoin/USD y oro con entradas M1, backtesting reproducible y herramientas de diagnóstico de MetaTrader 5 **exclusivamente en cuenta demo**.

> Estado actual: investigación/simulación. No hay evidencia de rentabilidad. La ejecución de órdenes está bloqueada por diseño en esta versión.

## Qué incluye

- Validación estricta de velas M1 cerradas.
- Seis detectores técnicos: soportes/resistencias, tendencia, Fibonacci, tres líneas, triángulos y Hombro-Cabeza-Hombro.
- Filtros de tendencia M15/H1/H4.
- Filtro de noticias point-in-time con cobertura explícita.
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
.\.venv\Scripts\python.exe -m bot replay --data bitcoin=btc_m1.csv --data gold=gold_m1.csv --out report-replay.json
.\.venv\Scripts\python.exe -m bot evaluate --data bitcoin=btc_m1.csv --data gold=gold_m1.csv --out report-evaluation.json
```

`evaluate` divide 70/30 por tiempo y compara la estrategia completa, cada detector aislado y la retirada de cada detector. No ajusta automáticamente parámetros.

## Riesgo de simulación

La configuración de ejemplo usa:

- riesgo por operación: 0,25 %;
- pérdida diaria: 2 %;
- máximo de posiciones: 2;
- riesgo abierto conjunto: 0,5 %;
- reward/risk: 2:1.

Son parámetros de investigación, no recomendaciones financieras.

## Noticias

`news.template.json` contiene cobertura vacía deliberadamente. Con `news.required=true`, la ausencia de cobertura bloquea las entradas. Esto evita tratar un archivo vacío como prueba de que no existían noticias.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La versión v2 tiene 21 pruebas locales aprobadas. Consulte `VALIDACION.md` para el alcance y las limitaciones.

## Próximos pasos

Consulte `ROADMAP.md`. La prioridad es validar lectura desde una cuenta MT5 demo, exportar histórico auténtico, comprobar especificaciones del broker y ejecutar evaluación fuera de muestra antes de construir un dashboard de monitoreo.
