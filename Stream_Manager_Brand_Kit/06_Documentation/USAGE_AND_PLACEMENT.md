# Using Stream Manager brand assets

## Home Assistant add-on / app
Copy `02_Home_Assistant_Addon/icon.png` and `logo.png` into the app directory beside `config.yaml`. The published recommended sizes are 128x128 and approximately 250x100 respectively. Avoid using the custom integration `brand/` folder for an add-on-only implementation.

## Custom integration (optional)
If you also create `custom_components/stream_manager/`, starting with Home Assistant 2026.3, include `brand/` directly in that integration directory. The separate `03_Optional_Integration_Brand` folder contains optional 256/512-sized integration assets.

## GitHub
- `github-social-preview.png`: upload to Settings > Social preview (1280x640, under 1 MB).
- `github-readme-banner.png`: put in repository's `images/` directory and link from README.
- `github-avatar-512.png`: optional repository/org avatar where supported.
- `github-architecture-concept.png`: concept-only diagram. Confirm actual implementation before implying features are live.
- `github-install-steps.png`: generic visual steps. Update descriptions if implementation differs.

## Correct positioning
Product name: Stream Manager
Short descriptor: Smart ONVIF proxy for Home Assistant
Expanded descriptor: A smart routing layer between ONVIF-compatible cameras and Home Assistant.

Use ONVIF as a protocol name in descriptions, not as a certification claim. No official partnership or Home Assistant association is implied. Avoid modifying or co-branding Home Assistant's trademarked house icon.

## General identity rules
- Minimum logo clear space: half of the mark's circle diameter around all edges.
- Do not stretch, skew, rotate, recolor individual routes, or apply drop-shadows to the mark.
- Use the light wordmark on dark backgrounds and dark wordmark on light backgrounds.
- Use the app tile for small-scale use; use horizontal lockup at wide sizes.
- Keep typography clear and short. Sentence case in body copy, title case for brand name.
