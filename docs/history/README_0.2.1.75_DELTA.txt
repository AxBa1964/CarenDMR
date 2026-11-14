CarenDMR 0.2.1.75 – Delta auf 0.2.1.74

Easy:
- zusätzlicher Button „Beenden“
- per TAB/Shift+TAB erreichbar
- Screenreader-Name „CarenDMR Easy beenden“
- Beenden bleibt in jedem Zustand verfügbar
- bei laufendem TX wird zuerst das TX-Stop-Signal gesetzt
- aktive BrandMeister-Verbindung wird vor dem Schließen best-effort getrennt
- Fehler/Timeout beim Trennen verhindern das Programmende nicht

Test:
  python -m pytest .\tests\test_easy_exit_02175.py -q
