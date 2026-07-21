# Contributing

Thank you for your interest in contributing! This project welcomes contributions from developers around the world — bug reports, translations, documentation improvements, and code are all appreciated.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Getting Started (Development Setup)](#getting-started-development-setup)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Translations](#translations)
- [Style Guide](#style-guide)
- [Recognition](#recognition)

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/). By participating, you agree to uphold a respectful, harassment-free environment for everyone, regardless of experience level, nationality, gender, or background.

## Ways to Contribute

You don't need to write code to contribute:
- 🐛 **Report bugs** — see [Reporting Bugs](#reporting-bugs)
- 💡 **Suggest features** — see [Suggesting Features](#suggesting-features)
- 🌍 **Translate the interface** — see [Translations](#translations)
- 📖 **Improve documentation** — fix typos, clarify instructions, add examples
- 🧪 **Test pre-release versions** and report feedback
- 💻 **Submit code** — bug fixes, new features, performance improvements

Look for issues labeled **`good first issue`** if you're new to the project, or **`help wanted`** for tasks we'd especially like help with.

## Getting Started (Development Setup)

1. **Fork** the repository and clone it locally:
   ```bash
   git clone https://github.com/geomatic-web/universal_map2web.git
   cd <plugin-repo>
   ```

2. **Install QGIS** (version 3.0+ recommended) if you don't already have it: https://qgis.org/download/

3. **Link the plugin folder** to your QGIS plugins directory so QGIS picks up your local changes:
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `C:\Users\<user>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

4. **Enable the plugin** in QGIS via `Plugins > Manage and Install Plugins`, and enable the **Plugin Reloader** plugin to speed up testing changes without restarting QGIS.

5. **Create a branch** for your change:
   ```bash
   git checkout -b fix/short-description
   ```

## Submitting Changes

1. Make your changes, keeping commits focused and descriptive.
2. Test your changes manually in QGIS (automated tests welcome where applicable).
3. Push your branch and open a **Pull Request** against the `main` branch.
4. In your PR description, explain:
   - What the change does and why
   - How you tested it
   - Any related issue number (e.g. `Fixes #12`)
5. Be responsive to review feedback — we aim to review PRs within a few days.

## Reporting Bugs

Open an issue on the GitHub tracker and include:
- QGIS version and OS
- Plugin version
- Steps to reproduce
- Expected vs. actual behavior
- Screenshots or error messages if available

## Suggesting Features

Open an issue describing:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you considered

## Translations

Both plugins currently support English and French. Adding a new language is one of the easiest and most valuable ways to contribute:

1. Locate the `.ts` translation file(s) in the `i18n/` folder.
2. Use **Qt Linguist** to translate the strings into your language.
3. Compile to `.qm` and submit a pull request with both files.

New language requests and partial translations are both welcome — you don't need to translate everything in one go.

## Style Guide

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Use descriptive variable and function names.
- Comment non-obvious logic, especially CRS/coordinate math or DOM/HTML generation.
- Keep pull requests focused on a single change when possible.

## Recognition

All contributors are credited in the project's `CONTRIBUTORS.md` file and in release notes. Thank you for helping make these tools better for the global QGIS community!
