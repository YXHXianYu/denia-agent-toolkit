# UI Templates

Default templates read by `scripts/unity-auto-play.py`:

- `play-button-idle.png`: top toolbar Play button in normal state.
- `play-button-active.png`: top toolbar Play button in active state.
- `renderdoc-capture-button.png`: Game view toolbar RenderDoc Capture button.

Guidelines:
- Crop only the target button itself.
- Keep idle and active Play templates aligned to the same button area so state switching is easier to verify.
- Crop only the RenderDoc capture button in the Game view toolbar.
- Do not include neighboring buttons, labels, or large background margins.
- Re-crop the template if Unity theme or DPI scaling changes significantly.
