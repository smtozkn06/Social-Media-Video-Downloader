# Social Media Video Downloader

🎥 **Modern and powerful social media video downloading platform**

## 🌟 Features

### Supported Platforms
- 📺 **YouTube** - Single video and playlist downloads
- 🎵 **TikTok** - Single and bulk video downloads
- 📸 **Instagram** - Photos, videos, and stories
- 📘 **Facebook** - Video downloads
- 🐦 **Twitter** - Media downloads
- 📌 **Pinterest** - Pin and collection downloads

### Key Features
- 🌍 **Multi-language Support** - Turkish and English
- 🎨 **Modern UI** - Clean and intuitive interface
- ⚡ **Fast Downloads** - Optimized download speeds
- 📁 **Bulk Downloads** - Download multiple videos at once
- 🎬 **Video Editor** - Built-in TikTok video editor
- 🔧 **Customizable Settings** - Personalize your experience
- 📱 **Responsive Design** - Works on all screen sizes

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Social-Media-Video-Downloader.git
   cd Social-Media-Video-Downloader
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

## 📖 Usage

1. **Launch the application** by running `python main.py`
2. **Select your language** (Turkish/English) on the splash screen
3. **Choose a platform** from the sidebar menu
4. **Enter the URL** of the content you want to download
5. **Click download** and wait for the process to complete

### Supported URL Formats

- **YouTube**: `https://www.youtube.com/watch?v=...` or `https://youtu.be/...`
- **TikTok**: `https://www.tiktok.com/@username/video/...`
- **Instagram**: `https://www.instagram.com/p/...` or `https://www.instagram.com/stories/...`
- **Facebook**: `https://www.facebook.com/watch/?v=...`
- **Twitter**: `https://twitter.com/username/status/...`
- **Pinterest**: `https://www.pinterest.com/pin/...`

## 🛠️ Technical Details

### Built With
- **Python 3.8+** - Core programming language
- **Flet** - Modern UI framework
- **yt-dlp** - Video downloading engine
- **Requests** - HTTP library for API calls
- **Threading** - Asynchronous operations

### Project Structure
```
Social-Media-Video-Downloader/
├── main.py                 # Main application entry point
├── splash_screen.py        # Splash screen with language selection
├── translations.py         # Multi-language support
├── video_processor.py      # Video processing utilities
├── settings.py            # Application settings
├── requirements.txt       # Python dependencies
├── modules/               # Platform-specific modules
│   ├── youtube/          # YouTube downloader
│   ├── tiktok/           # TikTok downloader
│   ├── instagram/        # Instagram downloader
│   ├── facebook/         # Facebook downloader
│   ├── twitter/          # Twitter downloader
│   └── pinterest/        # Pinterest downloader
├── output/               # Downloaded files (auto-created)
├── cookie/               # Browser cookies (auto-created)
├── logos/                # Logo files for video editing
└── README.md             # This file
```

## 🌐 Language Support

The application supports multiple languages:
- 🇹🇷 **Turkish** (Türkçe)
- 🇺🇸 **English**

Language can be changed on the splash screen or in the settings menu.

## ⚙️ Configuration

Settings are automatically saved in `settings.json`. You can customize:
- Default download directory
- Video quality preferences
- Language settings
- Theme preferences (Light mode)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect the terms of service of the platforms you're downloading from and ensure you have the right to download the content.

## 🐛 Bug Reports

If you encounter any bugs or issues, please [open an issue](https://github.com/yourusername/Social-Media-Video-Downloader/issues) with:
- Detailed description of the problem
- Steps to reproduce
- Your operating system and Python version
- Error messages (if any)

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Check the documentation
- Review existing issues for solutions

---

**Made with ❤️ for the community**