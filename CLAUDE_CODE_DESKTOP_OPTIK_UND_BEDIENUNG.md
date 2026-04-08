# Claude Code Desktop: Optik und Bedienung (Detailbeschreibung)

Stand: 8. April 2026  
Ziel: Detaillierte Beschreibung der visuellen Struktur und Interaktion der Claude Desktop App mit Fokus auf dem **Code-Tab (Claude Code Desktop)**.

## 1) Einordnung: Was ist „Claude Code Desktop“?

Claude Code Desktop ist kein separates Produkt, sondern der **Code-Tab innerhalb der Claude Desktop App**. Die Desktop-App bündelt drei Arbeitsmodi in einer Oberfläche:
- **Chat** (klassischer Dialog, ohne direkten Dateizugriff)
- **Cowork** (autonomer Aufgabenmodus)
- **Code** (interaktive Coding-Oberfläche mit lokalem Projektzugriff)

Diese Tabs werden laut offizieller Quickstart-Doku in der App sichtbar geführt, der Code-Tab sitzt oben zentral in der App-Navigation.

## 2) Optische Grundstruktur der Oberfläche

## 2.1 Tab- und Flächenaufbau

Die App folgt einer klaren Multi-Pane-Struktur:
- **Obere Modus-Navigation** zwischen Chat, Cowork und Code.
- **Linke Sidebar** für Sessions/Verläufe/Filter (je nach Modus).
- **Zentrale Arbeitsfläche** für Unterhaltung und Task-Ausführung.
- **Kontext- und Detailflächen** (z. B. Diff-Ansicht, Artifacts, Preview, CI-Status) erscheinen situationsbezogen innerhalb derselben Umgebung.

Im Code-Tab ist der Fokus sichtbar auf „Arbeitsfluss in einem Fenster“: Prompting, Änderungen prüfen, App testen, PR-Status verfolgen.

## 2.2 Prompt- und Steuerbereich

Im Code-Tab ist der Eingabebereich zugleich Schaltzentrale:
- **Promptfeld** für Aufgaben an Claude.
- **`+`-Button** neben dem Prompt für Anhänge, Skills, Connectoren, Plugins.
- **Model-Dropdown** direkt neben dem Senden-Button (vor Sessionstart fixierbar).
- **Mode-Selector** neben dem Senden-Button für Berechtigungs-/Autonomiegrad.

Visuell und funktional ist das ein „Command Center“-Muster: kurze Wege, alles in unmittelbarer Nähe des Promptfelds.

## 2.3 Sidebar-Verhalten

Im Code-Tab ist die Sidebar nicht nur Verlauf, sondern aktive Steuerung:
- `+ New session` zum parallelen Arbeiten.
- Filter nach **Status** (Active/Archived) und **Umgebung** (Local/Cloud).
- Session-spezifische Aktionen (z. B. archivieren).
- Dispatch-basierte Sessions werden mit Badge in der Sidebar gekennzeichnet.

## 2.4 Diff- und Review-Darstellung

Die Diff-UX ist zentraler visueller Baustein des Code-Tabs:
- Nach Änderungen erscheint ein **Diff-Stat-Indikator** (z. B. `+12 -1`).
- Klick öffnet den Diff-Viewer.
- **Dateiliste links**, **konkrete Änderungen rechts**.
- Inline-Kommentare auf Zeilenebene.
- Sammel-Submit von Kommentaren über `Cmd+Enter` (macOS) bzw. `Ctrl+Enter` (Windows).

Das ist ein klassisches „inspect -> comment -> iterate“-Pattern und wirkt wie ein integrierter PR-Preflight.

## 2.5 Preview- und CI-Flächen

Der Code-Tab integriert weitere visuelle Subpanels:
- **Embedded Preview** für laufende Dev-Server inkl. Interaktion im eingebetteten Browser.
- **Preview-Dropdown** zum Start/Stop/Config von Servern.
- **CI-Statusbar** nach PR-Erstellung mit Auto-fix/Auto-merge-Toggles.
- Desktop-Notifications bei Abschluss von CI-Läufen.

Dadurch entfällt häufiger Wechsel zwischen Editor, Browser, Terminal, CI-Webseite.

## 3) Bedienung nach Modus

## 3.1 Chat-Modus: Schnellzugriff und Kontextaufnahme

Desktop-spezifisch im Chat:
- **Quick Entry (macOS)** per Doppeltipp auf `Option`.
- Kompaktes Eingabefenster über laufenden Apps.
- Screenshot-Aufnahme und Window-Sharing direkt aus dem Overlay.
- Diktat via `Caps Lock` (mit Realtime-Transkription, macOS 14+).
- Shortcut-Varianten in `Settings > General` konfigurierbar.

Bedienlogik: „im Kontext bleiben“, statt aus dem aktuellen Task herauszureißen.

## 3.2 Cowork-Modus: Sichtbare Plan-/Fortschrittsführung

Cowork zeigt stärker agentische Bedienmuster:
- Mode-Wechsel über Chat/Cowork-Selector.
- Claude stellt initial Scope-Fragen und baut einen Plan.
- Fortschritt wird fortlaufend angezeigt (inkl. paralleler Workstreams).
- Geplante Tasks sind über „Scheduled“ in der linken Sidebar erreichbar.

Wichtig für das Bediengefühl: Cowork ist auf „delegieren und beobachten“ statt „jede Aktion einzeln treiben“ ausgelegt.

## 3.3 Code-Modus: Interaktive Entwicklungsarbeit

Typischer Ablauf:
1. Umgebung wählen (Local/Remote/SSH)
2. Projektordner wählen
3. Modell wählen
4. Permission Mode wählen
5. Aufgabe senden
6. Änderungen prüfen (Diff/Kommentare)
7. Optional Preview/CI/PR innerhalb derselben Oberfläche

Die Oberfläche zwingt nicht zum Tool-Hopping; sie bündelt Arbeitsphasen (Planen, Ändern, Prüfen, Ausliefern) in einer Session.

## 4) Berechtigungsmodell als UX-Prinzip

Ein zentrales Bedienkonzept ist die **graduelle Autonomie** über Modes:
- Ask permissions
- Auto accept edits
- Plan mode
- Auto (Preview/planabhängig)
- Bypass permissions (optional, explizit freizuschalten)

Wirkung auf die Bedienung:
- Einsteiger starten kontrolliert.
- Fortgeschrittene reduzieren Reibung über höhere Autonomie.
- Der Mode-Selector sitzt absichtlich direkt am Sende-Flow.

## 5) Computer Use als visuelle und interaktive Erweiterung

In Code/Cowork kann Claude (Preview-Feature) den Desktop bedienen:
- App-Zugriff via Prompt-gestützter Freigaben.
- Zugriffsstufen pro App-Kategorie (View only / Click only / Full control).
- Einstellungen in `Settings > General` (Computer use Toggle, denied apps, Window-Verhalten).
- Unter macOS zusätzlich Systemrechte für Accessibility + Screen Recording nötig.

Optisch relevant: Genehmigungen und Warnhinweise erscheinen direkt im Session-Flow statt als externes Admin-UI.

## 6) Artifacts und interaktive Connectoren

Auch außerhalb des Code-Tabs prägen diese Komponenten das UI-Verständnis der Desktop-App:
- **Artifacts** öffnen in einem eigenen Fensterbereich rechts der Konversation.
- Versionierung/Code-Ansicht/Copy/Download liegen direkt im Artifact-Bereich.
- Mehrere Artifacts lassen sich innerhalb derselben Konversation umschalten.
- **Interaktive Connectoren** erscheinen entweder als Inline-Karten oder Fullscreen-Ansicht innerhalb des Gesprächs.

Damit kombiniert die App textbasierten Dialog mit objektartigen Arbeitsflächen.

## 7) Plattformunterschiede (wichtig für Optik + Bedienung)

- **Quick Entry** ist laut Doku aktuell macOS-spezifisch.
- **Code-Tab/Claude Code Desktop** ist auf macOS und Windows verfügbar.
- **Linux** wird für die Desktop-App nicht unterstützt.
- Einige Funktionen sind planabhängig (z. B. Code-Tab, Cowork-Preview, Computer Use).

## 8) UX-Interpretation (aus Quellen abgeleitet)

Die folgenden Punkte sind **Interpretation** auf Basis der Dokumentation:
- Die UI ist klar auf „eine durchgehende Arbeitsoberfläche“ optimiert, nicht auf viele Spezialfenster.
- Das dominante Muster ist „Conversation-first, Tooling-second“: Prompting bleibt der Einstieg, aber visuelle Panels (Diff/Preview/Artifacts/CI) übernehmen dort, wo reiner Text zu langsam wäre.
- Die Informationsarchitektur priorisiert Kontrollierbarkeit: sichtbare Diffs, mode-basierte Autonomie, per-App-Freigaben.

## 9) Quellen (offiziell)

1. Claude Code Docs: Overview  
   https://code.claude.com/docs
2. Claude Code Docs: Get started with the desktop app  
   https://code.claude.com/docs/en/desktop-quickstart
3. Claude Code Docs: Use Claude Code Desktop  
   https://code.claude.com/docs/en/desktop
4. Claude Ressourcen: Navigating the Claude desktop app (Chat, Cowork, Code)  
   https://claude.com/resources/tutorials/navigating-the-claude-desktop-app
5. Claude Download/FAQ (Desktop vs Browser, Quick Entry, Extensions)  
   https://claude.com/download
6. Help Center: Installing Claude Desktop  
   https://support.claude.com/en/articles/10065433-installing-claude-desktop
7. Help Center: Use quick entry with Claude Desktop on Mac  
   https://support.claude.com/en/articles/12626668-use-quick-entry-with-claude-desktop-on-mac
8. Help Center: Get started with Cowork  
   https://support.claude.com/en/articles/13345190-get-started-with-cowork
9. Help Center: Let Claude use your computer in Cowork  
   https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork
10. Help Center: Use connectors to extend Claude's capabilities  
    https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
11. Help Center: Use interactive connectors in Claude  
    https://support.claude.com/en/articles/13454812-use-interactive-connectors-in-claude
12. Help Center: What are artifacts and how do I use them?  
    https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them
13. Help Center: How can I create and manage projects?  
    https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects
