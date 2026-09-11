# Validación v2

Fecha: 11 de septiembre de 2026.

Resultado local: **21 pruebas unitarias/de integración aprobadas**.

```text
python -m unittest discover -s tests -v
Ran 21 tests
OK
```

También se verificó una ejecución reproducible con velas sintéticas. Los datos sintéticos sirven exclusivamente para comprobar el software y sus métricas no representan resultados de mercado.

Cobertura relevante: validación de M1, marcos superiores completos, pivotes retrasados, ausencia de look-ahead, filtro de noticias, sizing, límites de riesgo, kill switch, journal persistente, prioridad conservadora de stop, replay, evaluación temporal, bloqueo de cuenta real y bloqueo explícito de envío de órdenes.

No validado todavía: conexión con un terminal MT5/XM del usuario, nombres reales de símbolos, contratos/costes del broker, histórico auténtico, noticias históricas verificables, ejecución demo ni rentabilidad fuera de muestra.
