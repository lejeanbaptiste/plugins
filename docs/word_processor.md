# XML Entity Plugin for Word Processors - Planning Document

## Overview

This document outlines the design and functionality of a **Zotero-like plugin** for LibreOffice and Microsoft Word. The plugin will allow users to insert and manage references to entities (e.g., people, books) stored in an XML database. The plugin will provide a **candidate window** for searching and selecting entities, and it will automatically format inserted fields based on their occurrence in the document.

---

## 🎯 Core Features

### 1. **Entity Database**

- **Source**: XML file with structured entries for:
  - **People**: Romanised names, Chinese characters, dates, nationality, descriptions.
  - **Books**: Titles (Romanised, Chinese), authors, dates, descriptions.
- **Assumption**: The XML structure is known and fixed. The plugin will not modify the XML schema but will read and sync with it.

### 2. **Candidate Window**

- **Trigger**: Opens via a **button** or **keyboard shortcut** (e.g., `Ctrl+Shift+E`).
- **Search**: Real-time filtering as the user types.
  - **Normalisation**: Ignores diacritics, capitalisation, and spaces.
  - **Fields searched**: Romanisation, Chinese characters, titles, authors.
  - **Mixed scripts**: Supports searching by Chinese characters (e.g., typing "李" matches "Li").
- **Results Display**:
  - Primary line: Romanised name + Chinese (if available).
  - Secondary line: Dates, nationality/author, and other metadata.
  - **Scrolling**: Defaults to 20 results; user can load more.
- **Keyboard Navigation**:
  - `↑↓` to navigate results.
  - `Enter` to select.
  - `Esc` to close.
- **Selection**: Inserts the chosen entity as a **field** into the document.

### 3. **Field Insertion &amp; Formatting**

- **Fields are immutable**: Users cannot edit them by typing; only via **right-click** or the **candidate window**.
- **Atomic Fields**: Each inserted field stores:
  - `entry_id` (link to XML database).
  - `field_type` (`person` or `book`).
  - `occurrence_index` (auto-calculated: `1` for first occurrence, `>1` for subsequent).
- **First Occurrence Rule**:
  - **Default**: First occurrence of an entity in the document shows **full details** (e.g., Romanised + Chinese + dates).
  - Subsequent occurrences show **shortened form** (e.g., Romanised name only).
  - **Configurable**: Users can toggle this rule via **panel settings**.
- **Right-Click Overrides**: For any field, users can force:
  - `family_only` (for people).
  - `given_only` (for people).
  - `full` (full name or title).
  - `full + chinese` (full name + Chinese characters).
  - `full + date` (full name + dates).
  - For books: `title_only`, `author_only`, `full`, `full + date`.

### 4. **Dynamic Recalculations**

- **Deletion Handling**: If a user deletes a field, the plugin **recalculates `occurrence_index`** for all instances of that `entry_id` in the document.
- **Editing Fields**: If a user edits a field (e.g., corrects a name or date), the plugin:
  - Prompts: *"Update database entry for \[Entity\]?"* (Yes/No).
  - If "Yes", updates the XML database and propagates changes to all instances of that `entry_id`.

### 5. **Database Sync**

- **Startup**: Auto-sync with the XML database to:
  - Validate `entry_id`s exist.
  - Update fields if database entries were edited externally.
- **Mid-Use Sync**:
  - **Sync button** in the plugin panel for manual triggering.
  - Handles external edits (e.g., user fixes a misspelled name in the XML file).

### 6. **Word Processor Support**


| Feature            | LibreOffice         | Microsoft Word      |
| ------------------ | ------------------- | ------------------- |
| Field insertion    | Custom field type   | Content Control     |
| Right-click menu   | Custom context menu | Custom context menu |
| Keyboard shortcuts | Configurable        | Configurable        |
| Sync button        | Panel/toolbar       | Ribbon tab          |


---

## 📌 Technical Details

### XML Schema Assumptions

- Each entry has a **unique `id`**.
- Fields for **people**:
  ```xml
  <person>
    <id>1</id>
    <romanised>Li Bai</romanised>
    <chinese>李白</chinese>
    <dates>701–762</dates>
    <nationality>Tang Dynasty</nationality>
    <description>Poet</description>
  </person>
  ```
- Fields for **books**:
  ```xml
  <book>
    <id>5</id>
    <title>Analects</title>
    <romanised>Lunyu</romanised>
    <chinese>论语</chinese>
    <author>Confucius</author>
    <dates>~5th Century BCE</dates>
    <description>Collection of sayings</description>
  </book>
  ```

### Field Metadata Structure

- Each inserted field is stored as:
  ```json
  {
    "entry_id": "1",
    "field_type": "person",
    "occurrence_index": 1,
    "display_format": "full" // or "family_only", "given_only", etc.
  }
  ```

### Performance Considerations

- **Indexing**: Preload XML into an **in-memory structure** (e.g., trie or SQLite) for fast fuzzy search.
- **Caching**: Cache search results per session.
- **Large Databases**: If the XML grows (&gt;10k entries), implement:
  - Lazy loading for candidate window results.
  - Background sync (non-blocking).

---

## 🎨 UI Mockups &amp; Workflows

### 1. **Candidate Window Workflow**

1. User presses shortcut (`Ctrl+Shift+E`) or clicks a toolbar button.
2. Candidate window opens with a search input.
3. User types to filter entities (e.g., "Li" or "李").
4. Results appear in real-time, showing:
  - Romanised name + Chinese.
  - Metadata (dates, nationality, etc.).
5. User navigates with `↑↓` and selects with `Enter`.
6. Field is inserted into the document.

### 2. **Field Interaction**

- **Right-click menu**:
  - Override formatting (e.g., "Show full name + dates").
  - Edit field (opens candidate window for that entity).
  - Delete field.
- **Visual distinction**: Fields may have a subtle background or underline to indicate they are managed by the plugin.

### 3. **Panel Settings**

- Toggle: *"Use first-occurrence formatting"* (ON/OFF).
- Sync button: *"Sync with Database"*.
- Keyboard shortcut customisation.

---

## 🔄 Edge Cases &amp; Error Handling


| Scenario                      | Handling                                                             |
| ----------------------------- | -------------------------------------------------------------------- |
| User deletes first occurrence | Recalculate `occurrence_index` for all instances of that `entry_id`. |
| XML file edited externally    | Auto-sync on startup; manual sync button for mid-use updates.        |
| Ambiguous search (e.g., "Li") | Show all matches; user can scroll or refine search.                  |
| Database entry deleted        | Flag fields linked to missing `entry_id` as "\[Entity not found\]".  |
| Field edited via right-click  | Prompt to update database; propagate changes to all instances.       |


---

## 📅 Next Steps

1. **Finalise XML schema** (if not already fixed).
2. **Prototype the candidate window** (React/HTML mockup).
3. **Implement field insertion logic** for LibreOffice/Word.
4. **Test sync and recalculation** workflows.
5. **Optimise for performance** (indexing, caching).

---

## 📝 Notes

- The plugin prioritises **immutability** of fields to prevent accidental edits.
- **First-occurrence rule** is global per document but can be disabled in settings.
- **Sync** ensures consistency between the document and the XML database.