---
name: rtl-cdc-linter
description: >
  Lint Verilog or SystemVerilog RTL for clock domain crossing (CDC) violations.
  Use this skill whenever the user asks to check for CDC issues, find unsynchronized
  crossings, review multi-clock designs, audit clock domain safety, or look for
  metastability risks in HDL code. Also trigger when the user pastes or points to
  an RTL module with multiple clocks and asks for a review, even if they don't
  explicitly say "CDC". This is a pre-EDA lint that catches issues early, before
  formal CDC tools like Spyglass or Meridian run.
---

# RTL CDC Linter Skill

Analyze Verilog/SystemVerilog RTL for clock domain crossing violations. Produce a
structured YAML report catching CDC issues early — before formal EDA tools run.

Scope: file-level (single module), small-to-mid scale. Not a replacement for
Spyglass or Meridian — think of it as a fast local lint pass.

## Analysis

Read the module and perform these steps in a single pass:

1. **Identify clock domains** — find every clock from `always_ff @(posedge ...)` blocks and edge expressions. Map each signal to its domain based on which clock drives it. Combinational signals inherit the domain of their inputs; mixed-domain combinational signals are crossing points.

2. **Detect crossings** — a crossing occurs when a signal from domain A is read in domain B. Check registered use (RHS of `always_ff`), combinational use (`always_comb`/`assign`), and port connections.

   **Deduplication:** One crossing per unique (signal, source_domain, dest_domain) tuple. If the same signal is used at multiple sites in the destination domain, list all lines under one entry — do not create duplicate entries.

3. **Classify** — determine if each crossing is synchronized. Recognize these patterns:
   - **2-FF / 3-FF synchronizer** — back-to-back FFs in destination domain (`*_m1`/`*_sync` naming). Safe for single-bit.
   - **Gray-code + sync** — Gray-encoded multi-bit bus through 2-FF. Safe for counters/pointers.
   - **Handshake / req-ack** — synced req one way, synced ack back, data stable between. Safe for multi-bit data.
   - **Toggle + snapshot** — source toggles flag and holds data; destination syncs toggle, samples on edge. Safe for multi-bit status.
   - **Pulse synchronizer** — pulse→toggle→sync→edge-detect. Safe for single-cycle events.
   - **Async FIFO** — dual-clock pointers via Gray-coded synchronizers. Safe for streams.

   If none of these patterns protect the crossing, it is a **violation**.

4. **Assess severity:**
   - **critical** — multi-bit unsynchronized (data corruption risk)
   - **high** — single-bit unsynchronized (metastability risk)
   - **medium** — partially synchronized or flawed sync (e.g., 2-FF on a narrow pulse that can be missed)
   - **low** — quasi-static or ambiguous (can't fully confirm)
   - **info** — properly synchronized

5. **Suggest fixes** for violations (medium and above): name the synchronizer pattern, say where to place it. For single-bit high violations, the fix is always "add a 2-FF synchronizer in the destination domain" — keep it brief.

## Output Format

Produce a single YAML document:

```yaml
module: <module_name>
file: <file_path>
clock_domains:
  - name: <clock_signal_name>

crossings:
  - id: CDC-<NNN>
    signal: <signal_name>
    width: <bit_width>
    source_domain: <clock_name>
    dest_domain: <clock_name>
    line: <line_number or list of lines where signal is consumed>
    direction: "<source_clock> -> <dest_clock>"
    synchronized: <true | false>
    sync_method: <"2ff" | "3ff" | "gray" | "handshake" | "toggle_snapshot" | "async_fifo" | "pulse_sync" | "none">
    severity: <"critical" | "high" | "medium" | "low" | "info">
    description: <one-line explanation>
    fix: <1-2 sentence remediation, omit for info-level>

summary:
  total_crossings: <N>
  violations: <N>
  by_severity:
    critical: <N>
    high: <N>
    medium: <N>
    low: <N>
    info: <N>
```

**Conventions:**
- Number IDs sequentially: CDC-001, CDC-002, etc.
- `line` = where the signal is *consumed*, not produced. Use a list `[42, 79]` for multiple sites.
- Only list **violations** (severity > info) in the crossings array. Do not list properly synchronized crossings — they add output bulk without actionable value. The summary `by_severity.info` count is sufficient to show that safe crossings were analyzed.
- `clock_domains` lists domain names only — do not enumerate every signal per domain.
- Keep `description` to one sentence. Keep `fix` to 1-2 sentences.

## Scope Limitations

- **Can do**: Single-module analysis, clock domain identification, synchronizer pattern recognition, unprotected crossing detection.
- **Cannot do**: Full IP hierarchy elaboration, generated clock analysis, SDC verification, or replace formal CDC tools.
- **When unsure**: Flag as `severity: low` with a note — do not silently ignore.

## Not Covered

- Reset domain crossings
- Glitch-free clock muxing
- Power-domain crossings
