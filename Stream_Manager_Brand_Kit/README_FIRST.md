# Stream Manager | Brand Kit

A complete identity handoff for **Stream Manager**, a smart ONVIF proxy project for Home Assistant.

## Included
- `Stream_Manager_Brand_Guidelines.pdf`: brand rationale, colors, identity usage, applications, handoff.
- `01_Logos/SVG`: resolution-independent vector source files.
- `01_Logos/PNG`: raster logo exports in dark, light, and one-color variants.
- `02_Home_Assistant_Addon/icon.png`: recommended 128x128 add-on/app icon. Copy directly to your add-on directory.
- `02_Home_Assistant_Addon/logo.png`: recommended 250x100 add-on/app logo. Copy directly to your add-on directory.
- `03_Optional_Integration_Brand/brand`: ONLY if you also publish a custom integration (not needed for an add-on-only repo).
- `04_GitHub`: social preview, README banners, architecture art, avatars, favicons, install art.
- `05_Design_Tokens`: palette JSON + CSS custom properties.
- `06_Documentation`: usage guidance, README examples, asset manifest, sourced dimension notes.
- `07_Artwork`: decorative illustration licensed as part of this delivered kit.

## Recommended repository layout

```text
my-addons/
  repository.yaml
  stream_manager/
    config.yaml
    icon.png  <-- copy from 02_Home_Assistant_Addon/
    logo.png  <-- copy from 02_Home_Assistant_Addon/
    README.md
    DOCS.md
  images/
    github-readme-banner.png
    github-architecture-concept.png
```

GitHub social preview must be uploaded in **Repository Settings > Social preview**.

## Scope notes
- This package creates visual identity assets, not the ONVIF proxy implementation.
- The architecture and install images are illustrative, not evidence of implemented features.
- Project is independent and is not an official Home Assistant or ONVIF-branded product. Do not represent it as official or certified without authorization.
- Do not substitute these custom images for Home Assistant's own protected logo.
