# Capture Shortcut Setup

The phone door into the capture system. Build once, use for years.

## Before you start

In the Files app, create a folder named `Capture` at the top level of
iCloud Drive. The sweep reads from there.

## Build the Shortcut

Shortcuts app → **+** → name it **Capture**.

Add these five actions in order:

1. **Dictate Text**
   - Language: English
   - Stop Listening: **After Pause**

2. **Text**
   - Content: the `Dictated Text` variable from step 1.
   - (This action exists so step 5 has a clean text input to write.)

3. **Format Date**
   - Date: **Current Date**
   - Format: **Custom**
   - Format String: `yyyyMMdd-HHmmss`

4. **Text**
   - Content: `capture-phone-`, then the `Formatted Date` variable from
     step 3, then `.txt` — all on one line with no spaces.

5. **Save File**
   - File: the `Text` from step 2
   - Service: **iCloud Drive**
   - Destination: `Capture` folder
   - **Ask Where to Save: OFF** ← this is the one that matters. Leave it
     on and the Shortcut stops to ask you a question every single time,
     which defeats the point.
   - **Overwrite If File Exists: OFF**
   - File Name: the `Text` from step 4

## Put it within reach

- **Home screen:** long-press the Shortcut → Share → Add to Home Screen.
- **Action Button** (iPhone 15 Pro and later): Settings → Action Button →
  Shortcut → Capture. This is the fastest path — one press from a locked
  phone, no unlocking to find an icon.
- **Back Tap** (any recent iPhone): Settings → Accessibility → Touch →
  Back Tap → Double Tap → Capture.

## Test it

1. Run the Shortcut and say: "testing the capture shortcut, this is a
   real thought about release checklists."
2. In Files, confirm `capture-phone-<timestamp>.txt` is in iCloud/Capture.
3. On the Mac, wait for iCloud to sync, then run `/review-inbox`.
4. Confirm the note appears with `source: phone` and the right timestamp.

## If a thought comes and the Shortcut feels like too much

Record a plain Voice Memo, or type into Apple Notes. Later, drop the text
into the iCloud `Capture` folder as a `.txt` file. The sweep picks up any
text file in that folder and tags it `source: unknown`. A messy capture
beats a lost thought.

## Troubleshooting

**Nothing appears in the inbox.** Check iCloud has synced — open the
Capture folder in Files on the Mac and confirm the file is there and
fully downloaded, not showing a cloud icon.

**The Shortcut asks where to save.** "Ask Where to Save" is still on in
the Save File action.

**Two notes for one thought.** Not possible — the sweep dedupes on
content, so re-running it is always safe.
