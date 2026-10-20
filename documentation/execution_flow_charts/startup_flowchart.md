# Startup Flowchart & Module Loading Sequence

This document details the exact loading sequence and module initialization flow of `new_reactor` when executed.

## Execution Timeline

The startup of the application is specifically optimized to show the user a splash screen instantaneously by deferring heavy backend imports until after the GUI has been drawn by the operating system.

```mermaid
sequenceDiagram
    participant OS as OS/Python
    participant Main as main.py
    participant Qt as Qt Event Loop
    participant Heavy as Heavy Modules
    participant UI as MstyCloneApp (UI)

    OS->>Main: python main.py
    Main->>Main: Import core PyQt5 modules (QApplication, QSplashScreen)
    Main->>Main: Set Qt Attributes (High DPI)
    Main->>Qt: app = QApplication(sys.argv)
    Main->>Main: Create QSplashScreen with splash.jpg
    Main->>Qt: splash.show() & app.processEvents()
    Note right of Qt: Splash Screen becomes visible instantly
    Main->>Main: Import standard & application modules (mainwindow, etc.)
    Main->>Qt: QTimer.singleShot(100ms, load_and_start)
    Main->>Qt: sys.exit(app.exec_()) (Start Event Loop)
    
    Note right of Qt: Wait 100ms to ensure Splash is rendered
    Qt->>Main: trigger load_and_start()
    
    Main->>Heavy: import da_patch, langchain, transformers, torch
    Heavy-->>Main: (Synchronous load, blocks for 2-3s)
    Main->>Heavy: da_patch.apply_deepagents_patches()
    
    Main->>UI: window = MstyCloneApp()
    Note over UI: UI widgets and layout initialized
    UI-->>Main: window created
    Main->>Qt: window.show()
    Main->>Qt: splash.finish(window)
    Note right of Qt: Splash Screen hides, Main Window appears
```

## Module Dependency Graph

This flowchart illustrates how the code pathways behave sequentially from execution to completion of the application loading sequence.

```mermaid
graph TD
    A[main.py Execution] --> B[Core Imports: sys, os, PyQt5.QtWidgets]
    B --> C[Configure Qt High DPI Attributes]
    C --> D[Initialize QApplication]
    D --> E[Show QSplashScreen]
    E --> F[Process Events to Render Splash]
    F --> G[Import Application Modules: mainwindow, etc.]
    G --> H[Schedule load_and_start in 100ms]
    H --> I[Start Qt Event Loop app.exec_]
    
    I -.->|Event loop triggers after 100ms| J(load_and_start execution)
    J --> K[Heavy Imports: langchain, deepagents, transformers, torch]
    K --> L[Apply deepagents Monkey Patches]
    L --> M[Initialize MstyCloneApp Main Window]
    M --> N[Show Main Window]
    N --> O[Finish Splash Screen]
    O --> P((Application Ready))
```

## Key Optimizations Noted
- **Deferred Heavy Imports:** Dependencies like `langchain`, `transformers`, and `deepagents` are isolated in `load_and_start()`.
- **Dynamic Thread Imports:** `GenerationThread` is intentionally not imported at the top-level of `mainwindow.py` to prevent cascading heavy imports during UI initializations.
- **Instant Paint:** `QApplication.processEvents()` is called immediately after `splash.show()` to bypass GIL lockups and enforce a render of the splash screen.
