import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import time
import threading
import schedule
from obswebsocket import obsws, requests, exceptions
import webbrowser
import pyautogui
import psutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
import pygetwindow as gw
from pywinauto import Application, findwindows
from pywinauto.controls.uiawrapper import UIAWrapper
import logging
import json
import re
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MeetingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Meeting + OBS + Zoom Launcher")
        self.root.geometry("600x500")
        
        # Initialize variables
        self.ws = None
        self.video_path = None
        self.zoom_driver = None
        self.zoom_joined = False
        self.mic_muted = False
        self.video_off = False
        self.extracted_passcode = None
        
        # OBS settings
        self.obs_websocket_host = "localhost"
        self.obs_websocket_port = 4455
        self.obs_websocket_password = "ashanb"
        self.obs_scene_name = "AutoScene"
        self.obs_media_name = "AutoMedia"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main title
        title_label = tk.Label(self.root, text="Meeting + OBS + Zoom Launcher", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Zoom Link Section
        self.create_zoom_section()
        
        # Audio/Video Settings Section
        self.create_av_settings_section()
        
        # OBS Video Selection Section
        self.create_obs_section()
        
        # Scheduling Section
        self.create_schedule_section()
        
        # Control Buttons
        self.create_control_buttons()
        
        # Status Section
        self.create_status_section()
        
        # Initialize UI state
        self.toggle_obs_options()
        self.toggle_time_entry()

    def create_zoom_section(self):
        """Create Zoom URL input section"""
        zoom_frame = tk.LabelFrame(self.root, text="Zoom Meeting", padx=10, pady=10)
        zoom_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(zoom_frame, text="Zoom Meeting URL:").pack(anchor="w")
        self.zoom_entry = tk.Entry(zoom_frame, width=60)
        self.zoom_entry.pack(pady=5, fill="x")

    def create_av_settings_section(self):
        """Create audio/video settings section"""
        av_frame = tk.LabelFrame(self.root, text="Audio/Video Settings", padx=10, pady=10)
        av_frame.pack(pady=5, padx=20, fill="x")
        
        self.mic_var = tk.BooleanVar(value=True)
        tk.Checkbutton(av_frame, text="Start with Microphone ON", 
                      variable=self.mic_var).pack(anchor="w")
        
        self.camera_var = tk.BooleanVar(value=True)
        tk.Checkbutton(av_frame, text="Start with Camera ON", 
                      variable=self.camera_var, 
                      command=self.toggle_obs_options).pack(anchor="w")

    def create_obs_section(self):
        """Create OBS video selection section"""
        obs_frame = tk.LabelFrame(self.root, text="OBS Virtual Camera", padx=10, pady=10)
        obs_frame.pack(pady=5, padx=20, fill="x")
        
        tk.Label(obs_frame, text="Select Video File for Virtual Camera:").pack(anchor="w")
        self.video_button = tk.Button(obs_frame, text="Select Video File", 
                                     command=self.select_video)
        self.video_button.pack(pady=5)
        
        self.video_label = tk.Label(obs_frame, text="No video selected", 
                                   fg="gray", wraplength=400)
        self.video_label.pack(pady=2)

    def create_schedule_section(self):
        """Create scheduling section"""
        schedule_frame = tk.LabelFrame(self.root, text="Meeting Schedule", padx=10, pady=10)
        schedule_frame.pack(pady=5, padx=20, fill="x")
        
        self.schedule_var = tk.StringVar(value="now")
        tk.Radiobutton(schedule_frame, text="Join Now", 
                      variable=self.schedule_var, value="now", 
                      command=self.toggle_time_entry).pack(anchor="w")
        tk.Radiobutton(schedule_frame, text="Schedule for Later", 
                      variable=self.schedule_var, value="scheduled", 
                      command=self.toggle_time_entry).pack(anchor="w")
        
        time_frame = tk.Frame(schedule_frame)
        time_frame.pack(fill="x", pady=5)
        tk.Label(time_frame, text="Time (HH:MM):").pack(side="left")
        self.time_entry = tk.Entry(time_frame, width=10)
        self.time_entry.pack(side="left", padx=10)

    def create_control_buttons(self):
        """Create control buttons"""
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.start_btn = tk.Button(button_frame, text="Start Meeting Flow", 
                                  command=self.start_workflow,
                                  bg="#0078d4", fg="white", 
                                  font=("Arial", 12, "bold"),
                                  padx=20, pady=10)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(button_frame, text="Stop & Cleanup", 
                                 command=self.stop_workflow,
                                 bg="#dc3545", fg="white", 
                                 font=("Arial", 12, "bold"),
                                 padx=20, pady=10)
        self.stop_btn.pack(side="left", padx=5)

    def create_status_section(self):
        """Create status display section"""
        status_frame = tk.LabelFrame(self.root, text="Status", padx=10, pady=10)
        status_frame.pack(pady=10, padx=20, fill="x")
        
        self.status_label = tk.Label(status_frame, text="Ready to start", 
                                   bg="lightgray", fg="black",
                                   font=("Arial", 10), relief="sunken",
                                   wraplength=500, justify="left")
        self.status_label.pack(fill="x", pady=5)

    def update_status(self, message, status_type="info"):
        """Update status display with color coding"""
        colors = {
            'success': {'bg': '#d4edda', 'fg': '#155724'},
            'error': {'bg': '#f8d7da', 'fg': '#721c24'},
            'info': {'bg': '#d1ecf1', 'fg': '#0c5460'},
            'working': {'bg': '#fff3cd', 'fg': '#856404'}
        }
        
        color_config = colors.get(status_type, colors['info'])
        self.status_label.config(text=message, bg=color_config['bg'], fg=color_config['fg'])
        self.root.update()
        logger.info(f"Status: {message}")

    def toggle_obs_options(self):
        """Toggle OBS options based on camera setting"""
        state = "normal" if self.camera_var.get() else "disabled"
        self.video_button.config(state=state)

    def toggle_time_entry(self):
        """Toggle time entry based on schedule setting"""
        if self.schedule_var.get() == "scheduled":
            self.time_entry.config(state="normal")
        else:
            self.time_entry.delete(0, tk.END)
            self.time_entry.config(state="disabled")

    def select_video(self):
        """Select video file for OBS"""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.wmv *.flv"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.video_path = file_path
            filename = os.path.basename(file_path)
            self.video_label.config(text=f"Selected: {filename}", fg="green")
            self.update_status(f"Video selected: {filename}", "success")
        else:
            self.update_status("No video selected", "info")

    def launch_obs(self):
        """Launch OBS Studio"""
        try:
            self.update_status("Launching OBS Studio...", "working")
            
            # Common OBS paths
            obs_paths = [
                r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
                r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
                "obs64.exe",  # If in PATH
                "obs.exe"     # Alternative name
            ]
            
            obs_launched = False
            for obs_path in obs_paths:
                try:
                    if os.path.exists(obs_path):
                        subprocess.Popen([obs_path])
                        obs_launched = True
                        break
                    else:
                        # Try to run from PATH
                        subprocess.Popen([obs_path])
                        obs_launched = True
                        break
                except (FileNotFoundError, OSError):
                    continue
            
            if not obs_launched:
                raise Exception("OBS Studio not found. Please install OBS Studio or check the installation path.")
            
            self.update_status("OBS Studio launched, waiting for startup...", "working")
            time.sleep(10)  # Wait for OBS to fully load
            
            return True
            
        except Exception as e:
            self.update_status(f"Failed to launch OBS: {str(e)}", "error")
            return False

    def connect_obs(self):
        """Connect to OBS WebSocket"""
        try:
            self.update_status("Connecting to OBS WebSocket...", "working")
            
            for attempt in range(10):
                try:
                    if self.ws:
                        try:
                            self.ws.disconnect()
                        except:
                            pass
                    
                    self.ws = obsws(self.obs_websocket_host, 
                                   self.obs_websocket_port, 
                                   self.obs_websocket_password)
                    self.ws.connect()
                    
                    self.update_status("Connected to OBS WebSocket!", "success")
                    return True
                    
                except exceptions.ConnectionFailure:
                    self.update_status(f"OBS connection attempt {attempt + 1}/10...", "working")
                    time.sleep(2)
                    
            raise Exception("Could not connect to OBS WebSocket after 10 attempts")
            
        except Exception as e:
            self.update_status(f"OBS WebSocket connection failed: {str(e)}", "error")
            return False

    def setup_obs_scene(self):
        """Setup OBS scene with video"""
        if not self.video_path or not self.ws:
            self.update_status("No video selected or OBS not connected", "error")
            return False

        try:
            self.update_status("Setting up OBS scene...", "working")
            
            # Get existing scenes
            scenes_response = self.ws.call(requests.GetSceneList())
            existing_scenes = [s['sceneName'] for s in scenes_response.getScenes()]

            # Create or use existing scene
            if self.obs_scene_name not in existing_scenes:
                self.ws.call(requests.CreateScene(sceneName=self.obs_scene_name))
                logger.info(f"Created new scene: {self.obs_scene_name}")

            # Get scene items
            items_response = self.ws.call(requests.GetSceneItemList(sceneName=self.obs_scene_name))
            items = items_response.getSceneItems()
            
            # Find existing media source
            media_item = next((item for item in items if item['sourceName'] == self.obs_media_name), None)

            if media_item:
                # Update existing media source
                self.ws.call(requests.SetInputSettings(
                    inputName=self.obs_media_name,
                    inputSettings={
                        "local_file": self.video_path,
                        "looping": True,
                        "restart_on_activate": True
                    }
                ))
                media_item_id = media_item['sceneItemId']
                logger.info(f"Updated existing media source: {self.obs_media_name}")
            else:
                # Create new media source
                self.ws.call(requests.CreateInput(
                    sceneName=self.obs_scene_name,
                    inputName=self.obs_media_name,
                    inputKind="ffmpeg_source",
                    inputSettings={
                        "local_file": self.video_path,
                        "looping": True,
                        "restart_on_activate": True
                    }
                ))
                logger.info(f"Created new media source: {self.obs_media_name}")
                
                # Get the new media item ID
                time.sleep(1)
                items_response = self.ws.call(requests.GetSceneItemList(sceneName=self.obs_scene_name))
                items = items_response.getSceneItems()
                media_item_id = next((item['sceneItemId'] for item in items 
                                    if item['sourceName'] == self.obs_media_name), None)

            if media_item_id is None:
                raise Exception("Could not find or create media scene item")

            # Configure scene item properties
            self.configure_scene_item(media_item_id)
            
            # Switch to the scene
            self.ws.call(requests.SetCurrentProgramScene(sceneName=self.obs_scene_name))
            
            self.update_status("OBS scene setup complete!", "success")
            return True
            
        except Exception as e:
            self.update_status(f"OBS scene setup failed: {str(e)}", "error")
            return False

    def configure_scene_item(self, media_item_id):
        """Configure scene item scaling and positioning"""
        try:
            # Get canvas dimensions
            video_settings = self.ws.call(requests.GetVideoSettings())
            canvas_width = video_settings.getVideoSettings().get('baseWidth', 1920)
            canvas_height = video_settings.getVideoSettings().get('baseHeight', 1080)
            
            # Get video dimensions using ffprobe
            video_width, video_height = self.get_video_dimensions()
            
            # Calculate scaling to fit canvas while maintaining aspect ratio
            scale_w = canvas_width / video_width
            scale_h = canvas_height / video_height
            scale = min(scale_w, scale_h)
            
            new_width = int(video_width * scale)
            new_height = int(video_height * scale)
            
            # Center the video
            pos_x = (canvas_width - new_width) / 2
            pos_y = (canvas_height - new_height) / 2
            
            # Apply transform
            self.ws.call(requests.SetSceneItemTransform(
                sceneName=self.obs_scene_name,
                sceneItemId=media_item_id,
                sceneItemTransform={
                    "positionX": pos_x,
                    "positionY": pos_y,
                    "scaleX": scale,
                    "scaleY": scale,
                    "alignment": 5  # Center alignment
                }
            ))
            
            logger.info(f"Video scaled to {new_width}x{new_height} and centered")
            
        except Exception as e:
            logger.warning(f"Scene item configuration failed: {e}")
            # Continue anyway with default settings

    def get_video_dimensions(self):
        """Get video dimensions using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json", 
                self.video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                video_info = json.loads(result.stdout)
                width = video_info['streams'][0]['width']
                height = video_info['streams'][0]['height']
                return width, height
            else:
                raise Exception("ffprobe failed")
                
        except Exception as e:
            logger.warning(f"Could not get video dimensions: {e}, using default 1920x1080")
            return 1920, 1080

    def start_virtual_cam(self):
        """Start OBS virtual camera"""
        try:
            self.update_status("Starting virtual camera...", "working")
            
            if not self.ws:
                if not self.launch_obs() or not self.connect_obs():
                    return False
            
            if not self.setup_obs_scene():
                return False
            
            # Start virtual camera
            self.ws.call(requests.StartVirtualCam())
            self.update_status("Virtual camera started successfully!", "success")
            return True
            
        except Exception as e:
            self.update_status(f"Virtual camera failed: {str(e)}", "error")
            return False

    def start_workflow(self):
        """Start the complete meeting workflow"""
        zoom_link = self.zoom_entry.get().strip()
        if not zoom_link:
            self.update_status("Please enter Zoom meeting URL", "error")
            messagebox.showerror("Error", "Please enter Zoom meeting URL")
            return

        self.start_btn.config(state="disabled", text="Running...")
        self.update_status("Starting meeting workflow...", "working")
        
        def run_workflow():
            try:
                success = True
                
                # Step 1: Setup OBS if camera is enabled
                if self.camera_var.get():
                    if not self.video_path:
                        self.update_status("Please select a video file for virtual camera", "error")
                        success = False
                    else:
                        self.update_status("Step 1/2: Setting up OBS virtual camera...", "working")
                        if not self.start_virtual_cam():
                            success = False
                        time.sleep(3)
                
                # Step 2: Join Zoom meeting
                if success:
                    self.update_status("Step 2/2: Joining Zoom meeting...", "working")
                    if self.join_zoom_meeting():
                        self.update_status("Meeting workflow completed successfully!", "success")
                        self.start_btn.config(text="Meeting Active", bg="#28a745")
                    else:
                        success = False
                
                if not success:
                    self.start_btn.config(state="normal", text="Start Meeting Flow", bg="#0078d4")
                    
            except Exception as e:
                self.update_status(f"Workflow failed: {str(e)}", "error")
                self.start_btn.config(state="normal", text="Start Meeting Flow", bg="#0078d4")

        # Handle scheduling
        if self.schedule_var.get() == "scheduled":
            time_str = self.time_entry.get().strip()
            if not time_str:
                self.update_status("Please enter scheduled time", "error")
                messagebox.showerror("Error", "Please enter scheduled time (HH:MM format)")
                self.start_btn.config(state="normal", text="Start Meeting Flow")
                return
            
            try:
                # Validate time format
                time.strptime(time_str, "%H:%M")
                schedule.every().day.at(time_str).do(run_workflow)
                threading.Thread(target=self.run_scheduler, daemon=True).start()
                self.update_status(f"Meeting scheduled for {time_str}", "success")
                self.start_btn.config(state="normal", text="Scheduled", bg="#ffc107")
            except ValueError:
                self.update_status("Invalid time format. Use HH:MM (24-hour format)", "error")
                messagebox.showerror("Error", "Invalid time format. Use HH:MM (24-hour format)")
                self.start_btn.config(state="normal", text="Start Meeting Flow")
        else:
            # Start immediately
            threading.Thread(target=run_workflow, daemon=True).start()

    def run_scheduler(self):
        """Run the scheduler in background"""
        while True:
            schedule.run_pending()
            time.sleep(1)

    def join_zoom_meeting(self):
        """Join Zoom meeting with improved popup handling"""
        zoom_link = self.zoom_entry.get().strip()
        
        try:
            self.update_status("Initializing browser for Zoom meeting...", "working")
            
            # Setup Chrome with comprehensive options
            chrome_options = Options()
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            
            # Enhanced preferences for protocol handling
            prefs = {
                "profile.default_content_setting_values": {
                    "protocol_handlers": 1,
                    "popups": 0,
                    "notifications": 2
                },
                "profile.managed_default_content_settings": {
                    "popups": 0
                },
                "profile.protocol_handler_per_host_allowed_protocols": {
                    "zoom.us": {"zoommtg": True, "zoomus": True},
                    "us04web.zoom.us": {"zoommtg": True, "zoomus": True},
                    "us05web.zoom.us": {"zoommtg": True, "zoomus": True}
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Initialize WebDriver
            self.zoom_driver = webdriver.Chrome(options=chrome_options)
            self.zoom_driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate to Zoom meeting
            self.update_status("Navigating to Zoom meeting...", "working")
            self.zoom_driver.get(zoom_link)
            
            # Handle the meeting join process
            return self.handle_meeting_join_process()
            
        except Exception as e:
            self.update_status(f"Failed to join meeting: {str(e)}", "error")
            if self.zoom_driver:
                try:
                    self.zoom_driver.quit()
                except:
                    pass
            return False

    def handle_meeting_join_process(self):
        """Handle the complete meeting join process with robust popup handling"""
        try:
            # Step 1: Handle cookies
            self.handle_cookie_consent()
            
            # Step 2: Handle browser protocol popup
            if self.handle_browser_protocol_popup():
                self.update_status("Browser popup handled, waiting for Zoom app...", "working")
                time.sleep(5)
                
                # Check if Zoom app opened
                if self.wait_for_zoom_app():
                    self.update_status("Zoom app detected, applying settings...", "working")
                    self.apply_zoom_settings()
                    return True
            
            # Step 3: Fallback to web-based join
            self.update_status("Trying web-based join as fallback...", "working")
            return self.handle_web_based_join()
            
        except Exception as e:
            self.update_status(f"Meeting join process failed: {str(e)}", "error")
            return False

    def handle_cookie_consent(self):
        """Handle cookie consent with multiple strategies"""
        try:
            self.update_status("Handling cookie consent...", "working")
            wait = WebDriverWait(self.zoom_driver, 5)
            
            # Strategy 1: JavaScript-based detection and clicking
            cookie_handled = self.zoom_driver.execute_script("""
                var cookieButtons = document.querySelectorAll('button, a, div');
                for (var i = 0; i < cookieButtons.length; i++) {
                    var element = cookieButtons[i];
                    var text = (element.textContent || element.innerText || '').toLowerCase();
                    var ariaLabel = (element.getAttribute('aria-label') || '').toLowerCase();
                    
                    if (text.includes('accept') || text.includes('agree') || 
                        ariaLabel.includes('accept') || ariaLabel.includes('agree')) {
                        if (text.includes('cookie') || text.includes('all') || 
                            ariaLabel.includes('cookie') || element.id.includes('cookie')) {
                            element.click();
                            return 'Clicked: ' + text;
                        }
                    }
                }
                return 'No cookie button found';
            """)
            
            if 'Clicked:' in cookie_handled:
                self.update_status("Cookie consent handled", "success")
                time.sleep(2)
                return True
            
            # Strategy 2: Selenium-based detection
            cookie_selectors = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
                "//button[contains(@id, 'accept')]",
                "//button[contains(@class, 'accept')]",
                "//*[@id='onetrust-accept-btn-handler']"
            ]
            
            for selector in cookie_selectors:
                try:
                    element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    element.click()
                    self.update_status("Cookie consent handled via Selenium", "success")
                    time.sleep(2)
                    return True
                except TimeoutException:
                    continue
            
            # Strategy 3: Keyboard navigation
            for _ in range(5):
                pyautogui.press('tab')
                time.sleep(0.5)
                pyautogui.press('enter')
                time.sleep(0.5)
            
            self.update_status("Cookie handling completed", "info")
            return True
            
        except Exception as e:
            logger.warning(f"Cookie handling error: {e}")
            return True  # Continue anyway

    def handle_browser_protocol_popup(self):
        """Handle browser protocol popup with multiple approaches"""
        try:
            self.update_status("Handling browser protocol popup...", "working")
            time.sleep(3)  # Wait for popup to appear
            
            # Strategy 1: Keyboard shortcuts (most reliable)
            keyboard_strategies = [
                lambda: pyautogui.press('enter'),  # Default button
                lambda: pyautogui.press('space'),  # Alternative activation
                lambda: pyautogui.hotkey('alt', 'o'),  # Alt+O for "Open"
                lambda: pyautogui.hotkey('ctrl', 'shift', 'enter'),  # Force open
            ]
            
            for i, strategy in enumerate(keyboard_strategies):
                try:
                    strategy()
                    time.sleep(2)
                    self.update_status(f"Tried keyboard strategy {i+1}", "info")
                except Exception as e:
                    logger.warning(f"Keyboard strategy {i+1} failed: {e}")
            
            # Strategy 2: Window automation with pywinauto
            try:
                chrome_windows = findwindows.find_windows(title_re=".*Chrome.*", class_name="Chrome_WidgetWin_1")
                
                for hwnd in chrome_windows[:3]:  # Limit to first 3 windows
                    try:
                        app = Application().connect(handle=hwnd)
                        window = app.window(handle=hwnd)
                        
                        # Look for buttons with relevant text
                        controls = window.descendants()
                        for control in controls:
                            try:
                                control_text = control.window_text().lower()
                                if any(keyword in control_text for keyword in ['open', 'launch', 'allow', 'continue']):
                                    control.click()
                                    self.update_status(f"Clicked popup button: {control_text}", "success")
                                    time.sleep(3)
                                    return True
                            except Exception:
                                continue
                                
                    except Exception as e:
                        logger.warning(f"Window automation attempt failed: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Window automation failed: {e}")
            
            # Strategy 3: Screen-based detection (if available)
            try:
                # Look for common button patterns on screen
                button_texts = ['Open Zoom', 'Launch Zoom', 'Open zoom.us', 'Continue']
                for button_text in button_texts:
                    try:
                        location = pyautogui.locateOnScreen(button_text, confidence=0.8)
                        if location:
                            pyautogui.click(pyautogui.center(location))
                            self.update_status(f"Found and clicked: {button_text}", "success")
                            time.sleep(3)
                            return True
                    except pyautogui.ImageNotFoundException:
                        continue
            except Exception as e:
                logger.warning(f"Screen detection failed: {e}")
            
            self.update_status("Protocol popup handling completed", "info")
            return True
            
        except Exception as e:
            logger.warning(f"Protocol popup handling failed: {e}")
            return True  # Continue anyway

    def wait_for_zoom_app(self):
        """Wait for Zoom app to open and become active"""
        try:
            self.update_status("Waiting for Zoom application...", "working")
            
            for attempt in range(30):  # Wait up to 30 seconds
                try:
                    # Look for Zoom windows
                    zoom_windows = gw.getWindowsWithTitle('Zoom')
                    zoom_windows.extend(gw.getWindowsWithTitle('zoom'))
                    
                    # Also check for Zoom processes
                    zoom_processes = []
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if 'zoom' in proc.info['name'].lower():
                                zoom_processes.append(proc)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    if zoom_windows or zoom_processes:
                        self.update_status("Zoom application detected!", "success")
                        time.sleep(2)  # Give it time to fully load
                        return True
                        
                except Exception as e:
                    logger.warning(f"Zoom detection attempt {attempt + 1} failed: {e}")
                
                time.sleep(1)
            
            self.update_status("Zoom app not detected, continuing with web version", "info")
            return False
            
        except Exception as e:
            logger.warning(f"Zoom app detection failed: {e}")
            return False

    def handle_web_based_join(self):
        """Handle web-based meeting join as fallback"""
        try:
            self.update_status("Joining via web browser...", "working")
            wait = WebDriverWait(self.zoom_driver, 10)
            
            # Look for web-based join options
            web_join_selectors = [
                "//a[contains(text(), 'join from your browser')]",
                "//a[contains(text(), 'Join from Your Browser')]",
                "//button[contains(text(), 'Join from Browser')]",
                "//a[contains(@href, 'wc/join')]"
            ]
            
            for selector in web_join_selectors:
                try:
                    element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    element.click()
                    self.update_status("Clicked web join option", "success")
                    time.sleep(3)
                    break
                except TimeoutException:
                    continue
            
            # Handle name input if required
            self.handle_name_input()
            
            # Look for final join button
            join_selectors = [
                "//button[contains(text(), 'Join')]",
                "//button[contains(text(), 'Join Meeting')]",
                "//input[@value='Join']"
            ]
            
            for selector in join_selectors:
                try:
                    element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    element.click()
                    self.update_status("Clicked join meeting button", "success")
                    time.sleep(3)
                    break
                except TimeoutException:
                    continue
            
            # Wait for meeting to load and apply settings
            return self.wait_for_meeting_controls()
            
        except Exception as e:
            self.update_status(f"Web-based join failed: {str(e)}", "error")
            return False

    def handle_name_input(self):
        """Handle name input in web version"""
        try:
            wait = WebDriverWait(self.zoom_driver, 5)
            
            name_selectors = [
                "//input[@placeholder*='name' or @placeholder*='Name']",
                "//input[@id='inputname']",
                "//input[@name='name']"
            ]
            
            for selector in name_selectors:
                try:
                    name_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    name_input.clear()
                    name_input.send_keys("Meeting Participant")
                    self.update_status("Name entered", "success")
                    return True
                except TimeoutException:
                    continue
                    
            return False
            
        except Exception as e:
            logger.warning(f"Name input handling failed: {e}")
            return False

    def wait_for_meeting_controls(self):
        """Wait for meeting controls to appear and apply initial settings"""
        try:
            self.update_status("Waiting for meeting to load...", "working")
            wait = WebDriverWait(self.zoom_driver, 30)
            
            # Look for meeting control indicators
            control_indicators = [
                "//button[contains(@aria-label, 'mute') or contains(@aria-label, 'microphone')]",
                "//button[contains(@aria-label, 'camera') or contains(@aria-label, 'video')]",
                "//*[contains(@class, 'meeting-control')]",
                "//*[contains(@class, 'footer-button')]"
            ]
            
            meeting_loaded = False
            for indicator in control_indicators:
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, indicator)))
                    meeting_loaded = True
                    break
                except TimeoutException:
                    continue
            
            if meeting_loaded:
                self.update_status("Meeting loaded successfully!", "success")
                time.sleep(2)
                self.apply_initial_settings()
                self.zoom_joined = True
                return True
            else:
                self.update_status("Meeting interface not detected, but connection established", "info")
                self.apply_initial_settings()  # Try anyway
                self.zoom_joined = True
                return True
                
        except Exception as e:
            self.update_status(f"Meeting load wait failed: {str(e)}", "error")
            return False

    def apply_zoom_settings(self):
        """Apply Zoom settings using keyboard shortcuts (for desktop app)"""
        try:
            time.sleep(3)  # Wait for Zoom to be ready
            
            # Focus on Zoom window
            zoom_windows = gw.getWindowsWithTitle('Zoom')
            if not zoom_windows:
                zoom_windows = gw.getWindowsWithTitle('zoom')
            
            if zoom_windows:
                zoom_windows[0].activate()
                time.sleep(1)
            
            self.apply_initial_settings()
            
        except Exception as e:
            logger.warning(f"Zoom settings application failed: {e}")

    def apply_initial_settings(self):
        """Apply initial microphone and camera settings"""
        try:
            time.sleep(2)  # Ensure meeting is ready
            
            # Apply microphone setting
            if not self.mic_var.get():  # User wants mic OFF
                pyautogui.hotkey('alt', 'a')  # Mute microphone
                self.update_status("Microphone muted as requested", "info")
                time.sleep(0.5)
            
            # Apply camera setting
            if not self.camera_var.get():  # User wants camera OFF
                pyautogui.hotkey('alt', 'v')  # Turn off camera
                self.update_status("Camera turned off as requested", "info")
                time.sleep(0.5)
            
            # Final status update
            mic_status = "OFF" if not self.mic_var.get() else "ON"
            camera_status = "OFF" if not self.camera_var.get() else "ON"
            self.update_status(f"Meeting active! Mic: {mic_status}, Camera: {camera_status}", "success")
            
        except Exception as e:
            logger.warning(f"Initial settings application failed: {e}")

    def stop_workflow(self):
        """Stop the workflow and cleanup resources"""
        try:
            self.update_status("Stopping workflow and cleaning up...", "working")
            
            # Close Zoom browser
            if self.zoom_driver:
                try:
                    self.zoom_driver.quit()
                    self.zoom_driver = None
                except:
                    pass
            
            # Disconnect from OBS
            if self.ws:
                try:
                    self.ws.call(requests.StopVirtualCam())
                except:
                    pass
                try:
                    self.ws.disconnect()
                    self.ws = None
                except:
                    pass
            
            # Reset UI
            self.start_btn.config(state="normal", text="Start Meeting Flow", bg="#0078d4")
            self.zoom_joined = False
            
            # Clear schedule
            schedule.clear()
            
            self.update_status("Workflow stopped and cleaned up", "success")
            
        except Exception as e:
            self.update_status(f"Cleanup failed: {str(e)}", "error")

    def __del__(self):
        """Cleanup when app is destroyed"""
        try:
            self.stop_workflow()
        except:
            pass


def main():
    """Main application entry point"""
    try:
        root = tk.Tk()
        app = MeetingApp(root)
        
        # Handle window closing
        def on_closing():
            try:
                app.stop_workflow()
            except:
                pass
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        messagebox.showerror("Error", f"Application failed to start: {e}")


if __name__ == "__main__":
    main()