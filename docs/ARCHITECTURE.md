# Cuyum v1.2 - Architecture

## Overview

FDSN / SeedLink -> station catalog -> candidate inventory -> live inventory organizer -> cell readers -> multicell fusion -> public server

## Core components
- app/cell_00_seedlink_reader.py: local cell reader.
- app/auto_cell_seedlink_reader.py: regional cell reader.
- app/live_inventory_organizer.py: builds local and regional sensor selections.
- app/multicell_fusion.py: combines cell state into network state.
- app/event_journal.py: stores recent runtime events.
- app/plain_python_server.py: HTTP server on port 5050.

## Public interfaces
- /app
- /json
- /reg

Runtime files are generated locally and are not versioned.
Cuyum is experimental and is not a certified earthquake early-warning system.
