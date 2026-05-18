"""Simplified Playwright browser controller with anti-crawler protections.

Extracted from WeChat_OA_Bot driver/playwright_driver.py.
Removed threading complexity (single-threaded standalone tool).
"""

import os
import sys
import json
import random
import uuid
import asyncio
import warnings
import gc
from urllib.parse import urlparse, unquote

try:
    warnings.filterwarnings("ignore", category=ResourceWarning)
except Exception:
    pass

browsers_name = os.getenv("BROWSER_TYPE", "firefox")

from playwright.sync_api import sync_playwright


class PlaywrightController:
    def __init__(self):
        self.driver = None
        self.browser = None
        self.context = None
        self.page = None
        self.isClose = True

    def _build_proxy_options(self, proxy_url: str):
        if not proxy_url:
            return None
        parsed = urlparse(proxy_url)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError(f"Invalid proxy URL: {proxy_url}")
        server = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port:
            server = f"{server}:{parsed.port}"
        proxy_options = {"server": server}
        if parsed.username:
            proxy_options["username"] = unquote(parsed.username)
        if parsed.password:
            proxy_options["password"] = unquote(parsed.password)
        return proxy_options

    def start_browser(self, headless=True, proxy_url="", browser_name=browsers_name):
        try:
            if str(os.getenv("NOT_HEADLESS", "False")).lower() == "true":
                headless = False
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            self.driver = sync_playwright().start()

            if browser_name.lower() == "firefox":
                browser_type = self.driver.firefox
            elif browser_name.lower() == "webkit":
                browser_type = self.driver.webkit
            else:
                browser_type = self.driver.chromium

            launch_options = {"headless": headless}

            if browser_name.lower() == "chromium":
                launch_options["args"] = [
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-webrtc",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--disable-default-apps",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            elif browser_name.lower() == "firefox":
                launch_options["firefox_user_prefs"] = {
                    "dom.webdriver.enabled": False,
                    "media.peerconnection.enabled": False,
                    "media.navigator.enabled": False,
                    "extensions.autoDisableScopes": 15,
                    "xpinstall.signatures.required": False,
                    "privacy.trackingprotection.enabled": True,
                    "privacy.trackingprotection.pbmode.enabled": True,
                    "toolkit.telemetry.enabled": False,
                    "datareporting.healthreport.uploadEnabled": False,
                    "browser.cache.disk.enable": True,
                    "browser.sessionstore.enabled": True,
                }
                launch_options["args"] = []
            else:
                launch_options["args"] = [
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-webrtc",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--disable-default-apps",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]

            proxy_options = self._build_proxy_options(proxy_url)
            if proxy_options:
                launch_options["proxy"] = proxy_options

            if sys.platform == "win32":
                launch_options["handle_sigint"] = False
                launch_options["handle_sigterm"] = False
                launch_options["handle_sighup"] = False

            self.browser = browser_type.launch(**launch_options)

            context_options = {
                "locale": "zh-CN",
                "user_agent": self._get_realistic_user_agent(),
                "viewport": {
                    "width": random.randint(1200, 1920),
                    "height": random.randint(800, 1080),
                    "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
                },
                "java_script_enabled": True,
                "ignore_https_errors": True,
                "bypass_csp": True,
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "no-cache",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                },
                "permissions": [],
            }

            self.context = self.browser.new_context(**context_options)
            self.page = self.context.new_page()
            self._apply_anti_crawler_scripts()
            self.isClose = False
            return self.page
        except Exception as e:
            self.cleanup()
            raise Exception(f"Browser launch failed: {e}")

    def _get_realistic_user_agent(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
        return random.choice(agents)

    def _apply_anti_crawler_scripts(self):
        self.page.add_init_script("""
        // WebDriver detection bypass
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // Chrome automation flags
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-client' }
                ];
                plugins.item = (i) => plugins[i] || null;
                plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
                plugins.refresh = () => {};
                return plugins;
            }
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });

        // WebRTC IP leak prevention
        if (window.RTCPeerConnection) {
            window.RTCPeerConnection = undefined;
        }
        if (window.webkitRTCPeerConnection) {
            window.webkitRTCPeerConnection = undefined;
        }

        // Canvas fingerprint randomization
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' && this.width === 220 && this.height === 30) {
                return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
            }
            const context = this.getContext('2d');
            if (context) {
                const imageData = context.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] ^= (Math.random() * 2) | 0;
                }
                context.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.apply(this, arguments);
        };

        // AudioContext fingerprint noise
        const audioContext = window.AudioContext || window.webkitAudioContext;
        if (audioContext) {
            const originalCreateAnalyser = audioContext.prototype.createAnalyser;
            audioContext.prototype.createAnalyser = function() {
                const analyser = originalCreateAnalyser.apply(this, arguments);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
                analyser.getFloatFrequencyData = function(array) {
                    for (let i = 0; i < array.length; i++) {
                        array[i] = -100 + Math.random() * 50;
                    }
                };
                return analyser;
            };
        }

        // WebGL fingerprint spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.apply(this, arguments);
        };
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter2.apply(this, arguments);
            };
        }

        // Font fingerprint noise
        const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
        CanvasRenderingContext2D.prototype.measureText = function(text) {
            const result = originalMeasureText.apply(this, arguments);
            result.width += Math.random() * 0.1 - 0.05;
            return result;
        };

        // Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Battery API spoofing
        if (navigator.getBattery) {
            navigator.getBattery = () => Promise.resolve({
                charging: true, chargingTime: 0, dischargingTime: Infinity, level: 1
            });
        }

        // Network Information API
        if (navigator.connection) {
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g', downlink: 10, rtt: 50, saveData: false
                })
            });
        }

        // Remove automation framework traces
        delete window.__playwright;
        delete window.__puppeteer;
        delete window.__selenium;
        delete window.__webdriver_evaluate;
        delete window.__selenium_evaluate;
        delete window.__fxdriver_evaluate;
        delete window.__driver_unwrapped;
        delete window.__webdriver_unwrapped;
        delete window.__selenium_unwrapped;
        delete window.__fxdriver_unwrapped;
        """)

    def open_url(self, url, wait_until="domcontentloaded"):
        self.page.goto(url, wait_until=wait_until)

    def Close(self):
        self.cleanup()

    def cleanup(self):
        errors = []
        for name, obj in [('page', self.page), ('context', self.context), ('browser', self.browser)]:
            if obj:
                try:
                    obj.close()
                except Exception as e:
                    errors.append(f"{name}: {e}")
        self.page = None
        self.context = None
        self.browser = None
        self.isClose = True
        gc.collect()

        if self.driver:
            try:
                self.driver.stop()
            except Exception:
                pass
            self.driver = None

    def __del__(self):
        try:
            self.Close()
        except Exception:
            pass
