# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of C-Bus MQTT Bridge integration
- GUI configuration through Home Assistant UI
- Support for TCP/CNI, Serial, and PCI interfaces
- Automatic device discovery
- Real-time state monitoring with polling fallback
- Bidirectional synchronization between C-Bus and Home Assistant
- Support for lights, switches, and fans
- Custom services for advanced C-Bus control
- HACS compatibility

### Features
- **Accurate State Tracking**: Real-time monitoring with polling fallback ensures lights show correct state
- **GUI Configuration**: Easy setup through Home Assistant configuration flow
- **Multiple Interface Support**: Works with TCP/CNI, Serial, and PCI connections
- **Auto-Discovery**: Automatically discovers C-Bus devices
- **Custom Services**: Advanced C-Bus control services for automation
- **Comprehensive Logging**: Detailed logging for troubleshooting

### Technical Details
- Built as proper Home Assistant integration
- Uses coordinator pattern for efficient state management
- Implements proper Home Assistant entity types
- Includes comprehensive error handling and recovery
- Supports Home Assistant's discovery and device registry

## [1.0.0] - 2025-01-XX

### Added
- Initial release 