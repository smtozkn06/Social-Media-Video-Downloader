# Contributing to Social Media Video Downloader

Thank you for your interest in contributing to Social Media Video Downloader! We welcome contributions from everyone.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- Basic knowledge of Python and GUI development

### Setting Up Development Environment

1. **Fork the repository**
   ```bash
   # Click the "Fork" button on GitHub, then clone your fork
   git clone https://github.com/yourusername/Social-Media-Video-Downloader.git
   cd Social-Media-Video-Downloader
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a new branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 📝 How to Contribute

### Types of Contributions

- 🐛 **Bug fixes**
- ✨ **New features**
- 📚 **Documentation improvements**
- 🌍 **Translations**
- 🎨 **UI/UX improvements**
- ⚡ **Performance optimizations**

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Screenshots** (if applicable)
- **Environment details** (OS, Python version, etc.)
- **Error messages** (full stack trace)

### Suggesting Features

Feature requests are welcome! Please:

- **Check existing feature requests** first
- **Provide clear use case** and rationale
- **Consider implementation complexity**
- **Be open to discussion** and feedback

## 🛠️ Development Guidelines

### Code Style

- Follow **PEP 8** Python style guide
- Use **meaningful variable names**
- Add **docstrings** to functions and classes
- Keep functions **small and focused**
- Use **type hints** where appropriate

### Project Structure

```
Social-Media-Video-Downloader/
├── main.py                 # Main application entry
├── splash_screen.py        # Splash screen with language selection
├── translations.py         # Multi-language support
├── video_processor.py      # Video processing utilities
├── settings.py            # Application settings
├── modules/               # Platform-specific modules
│   ├── youtube/          # YouTube downloader
│   ├── tiktok/           # TikTok downloader
│   ├── instagram/        # Instagram downloader
│   ├── facebook/         # Facebook downloader
│   ├── twitter/          # Twitter downloader
│   └── pinterest/        # Pinterest downloader
└── tests/                # Test files (to be added)
```

### Adding New Platform Support

To add support for a new platform:

1. **Create module directory** in `modules/`
2. **Implement scraper class** following existing patterns
3. **Add UI integration** in `main.py`
4. **Update translations** in `translations.py`
5. **Add platform icon** and styling
6. **Test thoroughly** with various content types

### Adding Translations

To add a new language:

1. **Edit `translations.py`**
2. **Add language code** to the translations dictionary
3. **Translate all keys** from existing languages
4. **Update language selection** in splash screen
5. **Test UI** with new language

### Testing

Before submitting:

- **Test your changes** thoroughly
- **Verify existing functionality** still works
- **Test on different platforms** if possible
- **Check for memory leaks** in long-running operations

## 📋 Pull Request Process

1. **Update documentation** if needed
2. **Add/update tests** for new functionality
3. **Ensure CI passes** (when implemented)
4. **Update CHANGELOG.md** with your changes
5. **Request review** from maintainers

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Other (please describe)

## Testing
- [ ] Tested locally
- [ ] Added/updated tests
- [ ] Verified existing functionality

## Screenshots
(If applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes
```

## 🌍 Translation Guidelines

### Current Languages
- 🇹🇷 Turkish (Türkçe)
- 🇺🇸 English

### Adding New Languages

1. **Check language support** in Flet framework
2. **Add language code** to `translations.py`
3. **Translate all text keys**
4. **Consider RTL languages** if applicable
5. **Test UI layout** with new language

### Translation Keys

- Use **descriptive key names**
- Keep **consistent naming** patterns
- Consider **text length** variations
- Test **UI overflow** with longer translations

## 🤝 Community Guidelines

- **Be respectful** and inclusive
- **Help newcomers** get started
- **Provide constructive feedback**
- **Follow code of conduct**
- **Ask questions** when unsure

## 📞 Getting Help

- **GitHub Issues** - For bugs and feature requests
- **GitHub Discussions** - For questions and ideas
- **Code Review** - For implementation feedback

## 🏆 Recognition

Contributors will be:
- **Listed in CONTRIBUTORS.md**
- **Mentioned in release notes**
- **Credited in documentation**

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Social Media Video Downloader!** 🎉