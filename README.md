# Meeting + OBS + Zoom Launcher

A comprehensive Python application that automates joining Zoom meetings with OBS virtual camera integration. This tool handles all the complex popup management and browser automation to seamlessly join meetings.

## Features

- **Automated Zoom Meeting Joining**: Handles all browser popups and protocol dialogs
- **OBS Virtual Camera Integration**: Automatically sets up and starts OBS virtual camera with your video
- **Smart Popup Handling**: Multiple strategies to handle OS-level and browser popups
- **Flexible Audio/Video Settings**: Choose initial microphone and camera states
- **Meeting Scheduling**: Join immediately or schedule for later
- **Robust Error Handling**: Comprehensive error management with detailed status updates
- **Clean UI**: Modern, organized interface with color-coded status updates

## Prerequisites

### Required Software

1. **Python 3.8+** - Download from [python.org](https://python.org)
2. **Google Chrome** - Latest version
3. **OBS Studio** - Download from [obsproject.com](https://obsproject.com)
4. **ChromeDriver** - Download from [chromedriver.chromium.org](https://chromedriver.chromium.org)
   - Make sure ChromeDriver version matches your Chrome version
   - Add ChromeDriver to your system PATH

### OBS Setup

1. Install OBS Studio
2. Enable WebSocket Server:
   - Go to **Tools** → **WebSocket Server Settings**
   - Check **Enable WebSocket server**
   - Set port to `4455` (default)
   - Set password to `ashanb` (or modify the code)
   - Click **OK**

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify ChromeDriver installation:**
   ```bash
   chromedriver --version
   ```

## Usage

1. **Run the application:**
   ```bash
   python meeting_app_cleaned.py
   ```

2. **Configure your meeting:**
   - Enter your Zoom meeting URL
   - Choose initial microphone and camera settings
   - If using virtual camera, select a video file
   - Choose to join now or schedule for later

3. **Start the workflow:**
   - Click "Start Meeting Flow"
   - The app will automatically:
     - Launch OBS (if needed)
     - Set up virtual camera (if enabled)
     - Open browser and navigate to Zoom
     - Handle all popups automatically
     - Join the meeting
     - Apply your audio/video preferences

## How It Works

### Popup Handling Strategy

The app uses multiple strategies to handle popups reliably:

1. **Keyboard Shortcuts**: Uses Enter, Space, Alt+O to activate default buttons
2. **Windows Automation**: Uses pywinauto to find and click specific UI elements
3. **Browser Automation**: JavaScript and Selenium to handle web-based popups
4. **Screen Recognition**: Falls back to image recognition when available

### OBS Integration

- Automatically launches OBS Studio if not running
- Connects to OBS WebSocket server
- Creates/updates a scene with your selected video
- Scales and centers video to fit canvas
- Starts virtual camera for use in Zoom

### Meeting Join Process

1. **Cookie Consent**: Automatically accepts cookie banners
2. **Protocol Popup**: Handles "Open Zoom Meetings" browser popup
3. **App Detection**: Waits for Zoom app to launch
4. **Fallback**: Uses web-based join if app doesn't launch
5. **Settings**: Applies your microphone and camera preferences

## Troubleshooting

### Common Issues

**"OBS Studio not found"**
- Install OBS Studio from the official website
- Make sure it's installed in the default location

**"Cannot connect to OBS WebSocket"**
- Open OBS Studio
- Enable WebSocket server in Tools → WebSocket Server Settings
- Check that port is 4455 and password matches

**"ChromeDriver not found"**
- Download ChromeDriver matching your Chrome version
- Add ChromeDriver to your system PATH
- Restart command prompt/terminal

**"Popup not handled"**
- The app uses multiple strategies and should handle most popups
- Try running as administrator if on Windows
- Check that Chrome is up to date

### Advanced Configuration

You can modify these settings in the code:

```python
# OBS WebSocket settings
self.obs_websocket_host = "localhost"
self.obs_websocket_port = 4455
self.obs_websocket_password = "ashanb"

# Scene and source names
self.obs_scene_name = "AutoScene"
self.obs_media_name = "AutoMedia"
```

## Features in Detail

### Status Updates
- **Green**: Success/completed actions
- **Red**: Errors that need attention  
- **Blue**: Informational messages
- **Yellow**: Work in progress

### Error Recovery
- Automatic retry mechanisms for network issues
- Graceful fallbacks when primary methods fail
- Comprehensive cleanup on errors

### Security
- Disables automation detection in Chrome
- Uses legitimate browser automation (not hacking)
- No credential storage or transmission

## Support

If you encounter issues:

1. Check the status messages for specific error details
2. Ensure all prerequisites are installed correctly
3. Try running as administrator (Windows)
4. Check that your Zoom link is valid and accessible

## License

This project is for educational and personal use. Respect Zoom's terms of service when using automated tools.

## Contributing

Feel free to submit issues and enhancement requests!
