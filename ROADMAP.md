# Roadmap

## Fase 1 — Base reproducible

- [x] Motor modular de mercado, señales, riesgo, noticias y backtest.
- [x] Evaluación temporal 70/30.
- [x] Suite de 21 pruebas.
- [x] GitHub Actions.
- [x] Bloqueo de cuentas reales y de `order_send`.

## Fase 2 — Validación MT5 demo

- [x] Descubrimiento de símbolos del broker.
- [x] Inspección de especificaciones del contrato.
- [x] Exportación de velas M1 cerradas.
- [ ] Ejecutar `mt5-inspect` en el terminal demo del usuario.
- [ ] Confirmar nombres exactos de Gold y Bitcoin.
- [ ] Exportar histórico auténtico de ambos instrumentos.
- [ ] Comparar spread, tick size, contract size y volumen con la configuración offline.

## Fase 3 — Evaluación

- [ ] Replay con histórico auténtico.
- [ ] Evaluación fuera de muestra.
- [ ] Walk-forward por ventanas temporales.
- [ ] Sensibilidad a spread, slippage y comisión.
- [ ] Analizar cada detector y combinaciones sin optimizar contra el test.

## Fase 4 — Datos externos

- [ ] Seleccionar proveedor de noticias con disponibilidad histórica point-in-time.
- [ ] Normalizar cobertura y eventos.
- [ ] Evaluar estrategia con y sin filtro de noticias.

## Fase 5 — Dashboard

- [ ] Dashboard de investigación separado del motor.
- [ ] Equity, drawdown, operaciones y bloqueos.
- [ ] Señales y explicaciones por detector.
- [ ] Estado de conexión MT5 demo y calidad de datos.

El proyecto permanecerá en investigación/paper/demo. No se habilitará ejecución con dinero real.
