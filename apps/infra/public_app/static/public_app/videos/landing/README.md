# SciTeX Public App Video Assets

This directory contains video assets used in the SciTeX public landing page.

## Current Videos

- **scholar-demo.mp4**: SciTeX Scholar module demonstration
- **writer-demo.mp4**: SciTeX Writer module demonstration
- **code-demo.mp4**: SciTeX Code module demonstration
- **viz-demo.mp4**: SciTeX Viz module demonstration
- **cloud-demo.mp4**: SciTeX Cloud module demonstration

## Thumbnails

- **thumbnails/scholar-demo.jpg**: Scholar video thumbnail
- **thumbnails/writer-demo.jpg**: Writer video thumbnail

## Video Guidelines

When adding new videos to this directory, please follow these guidelines:

1. **Naming Convention**: Use descriptive names with module/purpose (e.g., `module-name-demo.mp4`).

2. **Optimization**: Videos should be optimized for web delivery:
   - Use H.264 codec for maximum compatibility
   - Compress to a reasonable file size (aim for <5MB if possible for demo videos)
   - Use appropriate resolution (720p or 1080p recommended)

3. **Documentation**: Update this README when adding new videos.

4. **Thumbnails**: Create thumbnail images for video previews in `thumbnails/` subdirectory.

## Implementation Notes

Videos are integrated into the public landing page:

- Landing page demos section (`landing_demos.html`) - Module demonstration videos with autoplay

The embedded videos use autoplay, loop, and muted attributes for smooth demo presentation.

## License Information

These videos are proprietary to SciTeX and should not be redistributed without permission.

---

*Last updated: November 6, 2025*
