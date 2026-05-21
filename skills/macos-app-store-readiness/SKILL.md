---
name: macos-app-store-readiness
description: "Check macOS apps for App Store submission readiness and generate compliance reports. Use when the user wants to audit an app for App Store compliance, review App Store requirements, prepare a macOS app for distribution, or invokes /macos-app-store-readiness."
license: MIT
metadata:
  author: Mason-1011
  compatibility: claude-code
---

# macOS App Store Readiness Audit

A systematic audit framework for checking whether a macOS app project meets Apple's App Store submission requirements. Covers project configuration, sandbox, hardened runtime, code signing, notarization, privacy, review guidelines, network, UI/UX, and submission metadata.

**Output**: An HTML report saved to `{project_directory}/app-store-readiness-report.html` with severity-scored findings and specific remediation steps.

## Severity Levels

| Severity | Meaning | Blocks Submission? | Badge Color |
|----------|---------|-------------------|-------------|
| **Critical** | Will cause immediate App Store rejection | Yes — must fix | Red |
| **High** | Very likely to cause rejection or significant delay | Yes — should fix | Orange |
| **Medium** | May cause reviewer concern or questions | Recommended | Yellow |
| **Low** | Best practice, will not block approval | No | Gray |

**Category Status Rules:**
- **FAIL**: Any Critical or High finding exists
- **WARN**: Only Medium findings exist
- **PASS**: Only Low findings or no findings

## Analysis Workflow

When the user asks to audit a macOS app, follow these steps in order.

### Step 1: Project Discovery

Locate the project structure by running these commands:

```bash
# Find Xcode project
find "$PROJECT_DIR" -maxdepth 3 -name "*.xcodeproj" -o -name "*.xcworkspace" 2>/dev/null

# Find Info.plist files
find "$PROJECT_DIR" -name "Info.plist" -not -path "*/Pods/*" -not -path "*/Build/*" 2>/dev/null

# Find entitlements files
find "$PROJECT_DIR" -name "*.entitlements" 2>/dev/null

# Find privacy manifest
find "$PROJECT_DIR" -name "PrivacyInfo.xcprivacy" 2>/dev/null

# Find source code directories
find "$PROJECT_DIR" -type d -name "*.swift" -o -name "*.m" -o -name "*.h" 2>/dev/null | head -5
# Also check for top-level source dirs
ls "$PROJECT_DIR"/*.swift "$PROJECT_DIR"/Sources/ "$PROJECT_DIR"/App/ 2>/dev/null
```

**Determine project type** by grepping source code:
- SwiftUI: `import SwiftUI` or `@main` with `App` protocol
- AppKit: `import AppKit` or `NSApplication`
- Catalyst: `import UIKit` with macOS target
- Electron: `package.json` with `electron` dependency
- Flutter/React Native: corresponding config files

**Determine distribution type** by grepping `project.pbxproj`:
- `CODE_SIGN_IDENTITY` = `"Apple Distribution"` or `"3rd Party Mac Developer Application"` → Mac App Store
- `CODE_SIGN_IDENTITY` = `"Developer ID Application"` → Direct distribution (notarization required)
- `CODE_SIGN_IDENTITY` = `"Apple Development"` → Development only (not ready)

### Step 2: File Analysis

For each discovered file, read and extract relevant information:

**project.pbxproj** — grep for these build settings:
```bash
grep -E "(MACOSX_DEPLOYMENT_TARGET|ENABLE_HARDENED_RUNTIME|CODE_SIGN_IDENTITY|CODE_SIGN_ENTITLEMENTS|CODE_SIGN_STYLE|DEVELOPMENT_TEAM|PROVISIONING_PROFILE|PRODUCT_BUNDLE_IDENTIFIER|OTHER_CODE_SIGN_FLAGS|ARCHS|EXCLUDED_ARCHS|INFOPLIST_FILE|GENERATE_INFOPLIST_FILE)" project.pbxproj | sort -u
```

**Info.plist** — read and check for required keys. If `GENERATE_INFOPLIST_FILE = YES` in build settings, some keys may be in the build settings instead.

**Entitlements files** — read each `.entitlements` file and list all declared entitlements.

**PrivacyInfo.xcprivacy** — read and validate the structure (XML plist format).

**Source code** — scan for API usage patterns:
```bash
# Privacy APIs
grep -r "ATTrackingManager\|CNContactStore\|CLLocationManager\|AVCaptureDevice\|AVAudioSession\|PHPhotoLibrary\|EKEventStore\|CBCentralManager" --include="*.swift" --include="*.m" "$SRC_DIR"

# Networking
grep -r "NSURLConnection\|UIWebView\|WKWebView\|URLSession\|NSAppTransportSecurity" --include="*.swift" --include="*.m" "$SRC_DIR"

# Accessibility
grep -r "accessibilityLabel\|accessibilityIdentifier\|setAccessibilityLabel\|AccessibilityElement\|VoiceOver" --include="*.swift" --include="*.m" "$SRC_DIR"

# Deprecated APIs
grep -r "UIWebView\|UIAlertView\|UIActionSheet\|addressBookRef\|ABAddressBook" --include="*.swift" --include="*.m" "$SRC_DIR"

# IPv4 literals
grep -rE "\b[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\b" --include="*.swift" --include="*.m" --include="*.plist" "$SRC_DIR" | grep -v "127.0.0.1\|0.0.0.0\|255.255.255"

# Placeholder content
grep -ri "TODO\|FIXME\|lorem ipsum\|placeholder\|sample text" --include="*.swift" --include="*.m" --include="*.storyboard" --include="*.xib" "$SRC_DIR"

# StoreKit
grep -r "SKPaymentQueue\|StoreKit\|Product\|Transaction" --include="*.swift" "$SRC_DIR" | head -10

# ATT (App Tracking Transparency)
grep -r "ATTrackingManager\|requestTrackingAuthorization\|NSUserTrackingUsageDescription" --include="*.swift" --include="*.m" "$SRC_DIR"

# Third-party SDK privacy manifests
find "$PROJECT_DIR" -path "*/Pods/*" -name "PrivacyInfo.xcprivacy" -o -path "*/*.framework/*" -name "PrivacyInfo.xcprivacy" -o -path "*/*.xcframework/*" -name "PrivacyInfo.xcprivacy" 2>/dev/null

# Account deletion
grep -r "deleteAccount\|deleteUser\|removeAccount\|accountDeletion" --include="*.swift" "$SRC_DIR"
```

### Step 3: Checklist Evaluation

Go through each of the 10 categories below. For every checklist item, determine:
- **PASS**: Requirement is met
- **WARN**: Requirement is partially met or has concerns
- **FAIL**: Requirement is not met
- **N/A**: Requirement does not apply to this app (explain why)

### Step 4: Scoring

Calculate scores:
- **Category score**: PASS if all items pass or are N/A; WARN if only medium findings; FAIL if any Critical/High findings
- **Overall readiness**: `(passing categories / applicable categories) × 100%`
- Readiness gauge: Red (< 60%), Yellow (60-85%), Green (> 85%)

### Step 5: Generate HTML Report

Generate a self-contained HTML file (inline CSS, no external dependencies) and save it to `{project_directory}/app-store-readiness-report.html`. Use the report template specified at the end of this document.

After generating the report, print a summary to the user in the conversation:
1. Overall readiness percentage and category breakdown
2. Top 3 most critical items to fix first
3. If all categories pass, note the app appears ready for submission

---

## Category 1: Project Configuration

Verifies that the Xcode project and Info.plist are correctly configured for Mac App Store distribution.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| CFBundleIdentifier exists and is reverse-DNS format | Read Info.plist, check for valid `com.company.appname` | Critical | Add `CFBundleIdentifier` with valid reverse-DNS identifier (e.g., `com.yourcompany.appname`) |
| CFBundleName exists and is non-empty | Read Info.plist | Critical | Add `CFBundleName` (max 15 characters recommended) |
| CFBundleDisplayName exists | Read Info.plist | High | Add `CFBundleDisplayName` for the user-facing name |
| CFBundleVersion (build number) exists | Read Info.plist | Critical | Add `CFBundleVersion` (e.g., `"1"`, `"42"`) |
| CFBundleShortVersionString exists | Read Info.plist | Critical | Add `CFBundleShortVersionString` (e.g., `"1.0.0"`) |
| LSApplicationCategoryType is declared | Read Info.plist | High | Set to a valid UTI (e.g., `public.app-category.developer-tools`). See Apple's list of category UTIs. |
| NSHumanReadableCopyright exists | Read Info.plist | Medium | Add `NSHumanReadableCopyright` (e.g., `"Copyright 2026 Your Company"`) |
| Deployment target is recent | Grep `MACOSX_DEPLOYMENT_TARGET` in project.pbxproj | Medium | Set to macOS 13.0 or later (Apple periodically raises the minimum) |
| Architecture includes arm64 | Grep `ARCHS` / `EXCLUDED_ARCHS` in project.pbxproj | High | Ensure `arm64` is included for Apple Silicon. Use `$(ARCHS_STANDARD)` if unsure. |
| NSPrincipalClass is set | Read Info.plist | Medium | Set to `NSApplication` for AppKit apps. SwiftUI apps using `@main` may auto-set this. |
| CFBundleDocumentTypes correct (if applicable) | Read Info.plist | Medium | Ensure document type UTIs are valid and roles are correct |
| CFBundleURLTypes correct (if applicable) | Read Info.plist | Medium | Ensure URL scheme declarations have valid `CFBundleURLSchemes` |
| No legacy build system | Grep `UseNewBuildSystem` in project.pbxproj | Low | Remove `UseNewBuildSystem = NO` if present |

**Notes:**
- If `GENERATE_INFOPLIST_FILE = YES`, some keys may be auto-generated from build settings. Check both locations.
- If `INFOPLIST_FILE` points to a file that doesn't exist, this is a Critical finding.

---

## Category 2: App Sandbox

App Sandbox is **mandatory** for Mac App Store distribution. This category checks whether it is enabled and whether entitlements follow the principle of least privilege.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| App Sandbox is enabled | Check `.entitlements` for `com.apple.security.app-sandbox` = `true` | Critical | Enable App Sandbox in Xcode: target → Signing & Capabilities → + Capability → App Sandbox |
| Network client declared only if needed | Check for `com.apple.security.network.client` | Medium | Remove if the app does not make outgoing network connections |
| Network server declared only if needed | Check for `com.apple.security.network.server` | Medium | Remove if the app does not listen for incoming connections |
| File access entitlements are minimal | Check for `files.user-selected`, `files.downloads`, `files.home-relative`, `files.pictures`, `files.music`, `files.movies` | High | Use the narrowest scope possible. Prefer `user-selected` over `home-relative`. |
| No broad home directory access | Check for `com.apple.security.files.home-relative.read-write` | High | Downgrade to `read-only` or switch to `user-selected` (user picks files via Open dialog) |
| Device entitlements are justified | Check for `device.camera`, `device.audio-input`, `device.usb`, `device.bluetooth`, `print` | Medium | Remove any device entitlement the app does not actually use |
| Personal information entitlements justified | Check for `personal-information.addressbook`, `.location`, `.calendars`, `.photos-library` | Medium | Remove unused personal information entitlements |
| No temporary exception entitlements | Check for any key matching `com.apple.security.temporary-exception.*` | High | Remove temporary exceptions — they are heavily scrutinized by App Review and often rejected |
| No deprecated entitlements | Check for known deprecated keys | Medium | Replace deprecated entitlements with current equivalents |
| Entitlements file exists and is referenced | Check for `*.entitlements` file and `CODE_SIGN_ENTITLEMENTS` in build settings | Critical | Create an entitlements file and set `CODE_SIGN_ENTITLEMENTS` to its path in build settings |

**Notes:**
- For sandboxed apps, file access outside the container requires `NSOpenPanel`/`NSSavePanel` (Powerbox) or security-scoped bookmarks (`com.apple.security.files.bookmarks.app-scope`).
- If the app needs to access files across app launches, it must use security-scoped bookmarks with the `bookmarks.app-scope` entitlement.

---

## Category 3: Hardened Runtime

Hardened Runtime protects the app from code injection, dylib hijacking, and memory tampering. It is **required** for notarization and Mac App Store submission.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| Hardened Runtime is enabled | Grep `ENABLE_HARDENED_RUNTIME` in project.pbxproj | Critical | Set `ENABLE_HARDENED_RUNTIME = YES` in target Build Settings (Xcode: Signing & Capabilities → enable Hardened Runtime) |
| No unnecessary exception entitlements | Check `.entitlements` for `com.apple.security.cs.*` keys | High | Remove any exception not required by the app's actual runtime behavior |
| `allow-jit` only if needed | Check `com.apple.security.cs.allow-jit` | High | Remove unless the app is an interpreter or uses JavaScriptCore JIT |
| `allow-unsigned-executable-memory` only if needed | Check `com.apple.security.cs.allow-unsigned-executable-memory` | High | Remove unless the app uses frameworks that generate code at runtime (e.g., older Electron, some game engines) |
| `disable-library-validation` only if needed | Check `com.apple.security.cs.disable-library-validation` | High | Remove unless the app loads third-party plug-ins not signed by your team |
| `allow-dyld-environment-variables` removed | Check `com.apple.security.cs.allow-dyld-environment-variables` | High | Remove — this is a significant security risk and is rarely justified for App Store apps |
| `disable-executable-page-protection` removed | Check `com.apple.security.cs.disable-executable-page-protection` | High | Remove — this disables all W^X protections and is almost never justified |

**Notes:**
- Electron apps may need `allow-unsigned-executable-memory` and `disable-library-validation` depending on version. Newer Electron versions (28+) require fewer exceptions.
- Apps embedding Python, Lua, or other interpreters may need `allow-jit`.
- Each exception entitlement must be justified in the App Review notes.

---

## Category 4: Code Signing

All macOS apps must be properly code-signed. This category verifies the signing configuration.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| Code signing is enabled | Grep `CODE_SIGN_STYLE` in project.pbxproj; should be `Manual` or `Automatic` | Critical | Set `CODE_SIGN_STYLE = Automatic` or configure manual signing with proper identity |
| Signing identity is appropriate | Grep `CODE_SIGN_IDENTITY` in project.pbxproj | Critical | For Mac App Store: use `"Apple Distribution"` or `"3rd Party Mac Developer Application"`. For dev: `"Apple Development"` |
| Not using `--deep` signing | Grep `OTHER_CODE_SIGN_FLAGS` for `--deep` | High | Remove `--deep`. Sign each embedded framework/bundle individually instead. |
| No ad-hoc signing | Check that `CODE_SIGN_IDENTITY` is not `"-"` | High | Set to a proper Apple developer identity |
| Development team is set | Grep `DEVELOPMENT_TEAM` in project.pbxproj | High | Set `DEVELOPMENT_TEAM` to your 10-character Apple Team ID |
| Bundle identifier matches project | Compare `PRODUCT_BUNDLE_IDENTIFIER` in pbxproj with `CFBundleIdentifier` in Info.plist | High | Ensure they match (or use `$(PRODUCT_BUNDLE_IDENTIFIER)` in Info.plist) |
| Embedded frameworks are signed | If a built `.app` exists, run `codesign --verify --deep --strict YourApp.app` | High | Ensure each framework in `Contents/Frameworks/` is properly signed with the same team identity |
| No unsigned embedded content | Check for `.dylib`, `.framework`, `.appex` in the bundle | High | Sign all embedded binaries |

**Notes:**
- If a built `.app` bundle exists, run `codesign -dvv YourApp.app` to inspect actual signing state.
- `--deep` is considered harmful because it signs in an undefined order and may miss some items.

---

## Category 5: Notarization

Notarization is an automated Apple security check. It is **required** for Developer ID distribution (outside Mac App Store). For Mac App Store distribution, the App Store handles this — but configuration must still be correct.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| Distribution type detected | Check `CODE_SIGN_IDENTITY` for `"Developer ID Application"` vs `"Apple Distribution"` | Info | Determine which path applies |
| Hardened Runtime enabled (prerequisite) | See Category 3 | Critical | Must be enabled before notarization |
| App is notarized (Developer ID only) | If a built `.app` exists, run `spctl --assess --type execute --verbose 2 YourApp.app` | Critical (DevID) | Submit with `xcrun notarytool submit YourApp.zip --apple-id EMAIL --team-id TEAMID --wait` |
| Notarization ticket stapled (Developer ID only) | Run `xcrun stapler validate YourApp.app` | High (DevID) | Run `xcrun stapler staple YourApp.app` |
| DMG notarized (if distributing via DMG) | Check if DMG exists and validate | High (DevID) | Notarize the DMG separately |
| Using `notarytool` not deprecated `altool` | Check build scripts for `altool` references | Medium | Migrate to `xcrun notarytool` (available since Xcode 13) |

**Notes:**
- For **Mac App Store** distribution: notarization is handled by Apple during the upload process. These checks are informational.
- For **Developer ID** distribution: notarization is mandatory since macOS 10.15 Catalina. Apps will show a Gatekeeper warning if not notarized.

---

## Category 6: Privacy

Apple's privacy requirements are one of the most common rejection reasons. This category checks privacy manifests, usage descriptions, and tracking transparency.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| `PrivacyInfo.xcprivacy` exists | Search project for `PrivacyInfo.xcprivacy` | Critical | Create a privacy manifest (Xcode: File → New → Privacy Manifest) |
| Privacy manifest declares `NSPrivacyTracking` | Read `PrivacyInfo.xcprivacy` | High | Set to `true` if app uses data for tracking, `false` otherwise |
| Privacy manifest declares `NSPrivacyTrackingDomains` | Read `PrivacyInfo.xcprivacy` | High | List all domains used for tracking (e.g., analytics endpoints) |
| Privacy manifest declares `NSPrivacyCollectedDataTypes` | Read `PrivacyInfo.xcprivacy` | High | Declare all collected data types with their purposes and whether linked to identity |
| Privacy manifest declares `NSPrivacyAccessedAPITypes` | Read `PrivacyInfo.xcprivacy` | High | Declare all Required Reason APIs used (see list below) |
| `NSCameraUsageDescription` present (if camera used) | Read Info.plist; check for `AVCaptureDevice` in source | Critical | Add a clear, user-facing description of why the app needs camera access |
| `NSMicrophoneUsageDescription` present (if mic used) | Read Info.plist; check for `AVAudioSession` recording in source | Critical | Add description of microphone usage |
| `NSLocationWhenInUseUsageDescription` present (if location used) | Read Info.plist; check for `CLLocationManager` in source | Critical | Add description of location usage |
| `NSContactsUsageDescription` present (if contacts used) | Read Info.plist; check for `CNContactStore` in source | Critical | Add description of contacts usage |
| `NSPhotoLibraryUsageDescription` present (if photos used) | Read Info.plist; check for `PHPhotoLibrary` in source | Critical | Add description of photo library usage |
| `NSBluetoothAlwaysUsageDescription` present (if Bluetooth used) | Read Info.plist; check for `CBManager` in source | Critical | Add description of Bluetooth usage |
| `NSCalendarsUsageDescription` present (if calendar used) | Read Info.plist; check for `EKEventStore` in source | Critical | Add description of calendar usage |
| App Tracking Transparency implemented (if tracking) | Search source for `ATTrackingManager` | Critical | Implement `ATTrackingManager.requestTrackingAuthorization` before any tracking |
| ATT prompt is not shown unnecessarily | Check if ATT is shown only when actual cross-app tracking occurs | High | Do not show ATT if the app does not track users across apps/websites — Apple rejects unnecessary prompts |
| Third-party SDK privacy manifests present | Check embedded frameworks/Swift Packages for `PrivacyInfo.xcprivacy` | High | Ensure every third-party SDK ships its own privacy manifest. Update SDK versions if manifests are missing. |
| Privacy nutrition labels match actual collection | Cross-reference manifest declarations with App Store privacy label | High | Apple cross-references manifests with nutrition labels and network traffic — mismatches cause rejection |
| Account deletion implemented (if accounts exist) | Search source for account creation/deletion patterns | High | Implement account deletion per Guideline 5.1.1(v) — must be easily discoverable |
| Privacy policy URL provided | Check metadata or Info.plist for privacy URL | High | Add a valid, accessible privacy policy URL |
| No deprecated privacy-sensitive APIs | Search for `UIWebView`, deprecated address book APIs | Medium | Replace with modern equivalents (`WKWebView`, `CNContactStore`) |

**Required Reason APIs** (must be declared in `PrivacyInfo.xcprivacy` if used):

| API Category | Examples | Required Reason Codes |
|-------------|----------|----------------------|
| File timestamp | `NSFileCreationDate`, `NSFileModificationDate`, `NSURLContentModificationDateKey` | `DDA9.1` (app functionality), `C617.1` (declared reason) |
| System boot time | `systemUptime`, `mach_absolute_time()` | `35F9.1` (app functionality) |
| Disk space | `volumeAvailableCapacityKey`, `NSURLVolumeAvailableCapacityForImportantUsageKey` | `E174.1` (app functionality) |
| User defaults | `UserDefaults`, `NSUserDefaults` | `CA92.1` (app functionality), `1C8A.1` (cross-app consistency) |
| Active keyboard | `GCKeyboard`, `UIKeyCommand` | `3EC1.1` (app functionality) |

**ATT Implementation Pattern (macOS):**

```swift
import AppTrackingTransparency

func requestTrackingPermission() async {
    let status = await ATTrackingManager.requestTrackingAuthorization()
    switch status {
    case .authorized:
        // Enable tracking, initialize ad SDKs with tracking
        break
    case .denied, .restricted:
        // Use non-personalized ads, disable cross-app tracking
        break
    case .notDetermined:
        // Should not happen after request, handle gracefully
        break
    @unknown default:
        break
    }
}
```

**Timing:** Request ATT permission after the app has launched and the user has context. Do not show the prompt immediately on first launch.

**Usage Description String Quality** — Apple rejects vague descriptions:

```
// REJECTED — too vague
"This app needs access to your camera."

// APPROVED — specific purpose
"The camera is used to scan barcodes for price comparison."

// REJECTED — too vague
"This app needs your location."

// APPROVED — specific purpose
"Your location is used to show nearby restaurants on the map."
```

---

## Category 7: App Store Review Guidelines

Maps the most commonly cited rejection reasons to concrete checks.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| No placeholder content | Search for `TODO`, `FIXME`, `lorem ipsum`, placeholder images, empty views | High | Remove all placeholder content before submission |
| No crash-on-launch bugs | Test basic launch flow on a clean install | Critical | Fix crash; test on a fresh macOS user account |
| Metadata matches functionality | Compare app description with actual features | High | Update metadata to accurately describe what the app does |
| App provides meaningful functionality | Review feature set | High | Ensure the app is more than a web wrapper or thin shell |
| In-app purchases use StoreKit | Search for `SKPaymentQueue`, `StoreKit` framework usage | Critical | Implement all digital purchases through StoreKit. No external payment links. |
| No external payment mechanisms | Search for external purchase URLs, QR codes for payment | Critical | Remove any payment mechanism that bypasses Apple's IAP per Guideline 3.1.1 |
| Restore purchases implemented | Search for `restoreCompletedTransactions` or `Transaction.currentEntitlements` | High | Users must be able to restore previous purchases. Implement restore button for non-consumables and subscriptions. |
| Transaction verification present | Search for `Transaction.currentEntitlements` or server-side validation | Medium | Use StoreKit 2 `Transaction.currentEntitlements` or server-side receipt validation |
| Subscription terms are clear | Check for subscription UI with terms disclosure | High | Price, duration, and auto-renewal terms must be clearly displayed before purchase. Free trials must state what happens when they end. |
| Interrupted purchases handled | Search for `pending`, `deferred`, `Transaction.updates` | Medium | Handle interrupted purchases, deferred transactions (Ask to Buy), and interrupted downloads gracefully |
| UGC moderation (if user-generated content) | Check for reporting, blocking, filtering features | Critical | Implement content moderation per Guideline 1.2 |
| No fake system UI | Check for custom alerts mimicking macOS system dialogs | High | Remove fake system alerts; use `NSAlert` for standard dialogs |
| Error handling is graceful | Check for proper error states, no raw error codes shown to users | Medium | Implement user-friendly error messages |
| App works offline (if applicable) | Check for offline state handling | Medium | Implement offline mode or clear messaging when connectivity is required |
| No objectionable content | Review app content and features | Critical | Remove content violating Guideline 1.1 (Safety) |
| Age rating is accurate | Check content declarations | Medium | Set accurate age rating based on actual content |
| No cryptocurrency mining | Search for mining-related code or libraries | Critical | Remove any mining functionality |
| App doesn't require device restart | Check for instructions suggesting restart | High | Remove any requirement to restart or modify system settings |

---

## Category 8: Network and Connectivity

Apps must work correctly on modern networks, including IPv6-only environments.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| No hardcoded IPv4 addresses | Grep source for `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` (excluding 127.0.0.1, 0.0.0.0, 255.255.255) | Critical | Replace all IPv4 literals with DNS hostnames or use `getaddrinfo()` for IPv6 compatibility |
| Uses modern networking APIs | Search for `NSURLConnection` (deprecated) | Medium | Migrate to `URLSession` |
| Uses WKWebView not UIWebView | Search for `UIWebView` usage | High | Replace `UIWebView` with `WKWebView` — `UIWebView` is deprecated and will cause rejection |
| App Transport Security configured | Check `NSAppTransportSecurity` in Info.plist | Medium | Use HTTPS for all connections. Avoid `NSAllowsArbitraryLoads = true`. |
| Network entitlements match usage | Cross-reference entitlements with actual network code | Medium | Remove unused network entitlements; add missing ones |
| IPv6-only network testing | Check for any IPv6-incompatible patterns | High | Test on an IPv6-only network. Apple's review environment may be IPv6-only. |
| Background networking configured (if needed) | Check for background mode declarations | Low | Configure background fetch or remote notification if the app needs to work in the background |

---

## Category 9: UI/UX and Accessibility

Apps must follow Apple's Human Interface Guidelines and support accessibility features.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| VoiceOver accessibility labels | Search for `accessibilityLabel`, `setAccessibilityLabel`, `.accessibilityLabel` in UI code | High | Add accessibility labels to all interactive elements and meaningful images |
| Supports Dynamic Type / text scaling | Check for use of system fonts or `NSFont.preferredFont(forTextStyle:)` | Medium | Use system fonts or text styles for automatic scaling |
| Dark mode support | Check for `NSAppearance` handling, dark/light asset variants | Medium | Support both light and dark appearances. Use semantic colors. |
| Keyboard navigation support | Check for key view loop, keyboard shortcuts, `@IBAction` | Medium | Ensure all interactive elements are keyboard-accessible |
| Standard menu bar items | Check for Edit, File, Window, Help menus | Medium | Include standard macOS menus (Undo, Cut, Copy, Paste, etc.) |
| Minimum window size is reasonable | Check `NSWindow` minimum/maximum size constraints | Medium | Set a reasonable minimum size so the UI doesn't break at small sizes |
| Uses standard macOS controls | Check for native AppKit/SwiftUI controls vs custom implementations | Medium | Prefer standard controls for consistent platform experience |
| Respects system accessibility settings | Check for reduced motion, increased contrast handling | Low | Honor `NSWorkspace.shared.accessibilityDisplayShouldReduceMotion` and similar settings |
| Toolbar follows HIG (if applicable) | Check toolbar implementation | Low | Follow HIG toolbar patterns: primary actions, customization support |
| Touch Bar support (if applicable) | Check for `NSTouchBar` implementation | Low | Add Touch Bar items for MacBook Pro users |

---

## Category 10: Submission Readiness

Metadata and App Store Connect readiness checklist.

| Check | How to Verify | Severity | Remediation |
|-------|--------------|----------|-------------|
| App description is complete | Check documentation or metadata files | High | Write clear, accurate description (up to 4000 characters). Must not contain prices (they vary by region) or competitor references. |
| App name is optimized | Check metadata | Medium | 30 characters max. Must be unique on the App Store. No generic terms ("Photo Editor" alone), no competitor names, no pricing info. |
| Screenshots provided | Check for screenshot files or documentation | Critical | Capture at required sizes: 1280×800, 1440×900, 2560×1600, or 2880×1800. Screenshots must show actual app UI — no mockups or marketing renders. |
| App Preview videos (optional) | Check for video files | Low | Up to 3 preview videos per localization, 30 seconds max. Must show the actual app running on device. |
| Keywords optimized | Check metadata | Medium | 100 characters max, comma-separated. Do not duplicate app name or subtitle. Use singular only ("game" not "game,games"). No competitor names. |
| Support URL provided | Check metadata | High | Add a valid, working support URL |
| Privacy policy URL provided | Check metadata or Info.plist | Critical | Add a valid privacy policy URL (required for all apps) |
| Demo account provided (if login required) | Check documentation | High (if applicable) | Provide non-expiring demo credentials in App Review notes. Most Guideline 2.1 rejections are from reviewers unable to log in. |
| Review notes explain app | Check documentation | Medium | Write detailed review notes explaining app functionality and any non-obvious features. Include test instructions for hardware-dependent features. |
| Copyright information correct | Check metadata | Medium | Include year and entity name (e.g., "Copyright 2026 Your Company") |
| Export compliance declared | Check for `ITSAppUsesNonExemptEncryption` in Info.plist | Medium | Set to `true` or `false`. If `true`, you may need to submit annual self-classification to the U.S. Bureau of Industry and Security. |
| Version numbers are correct | Check `CFBundleVersion` and `CFBundleShortVersionString` | Medium | Ensure build number is incremented from previous submission |
| No debug/test configurations in release | Check for `#if DEBUG`, test flags, `DEBUG` preprocessor macros | High | Ensure release build does not contain debug-only code paths |
| App Icon is complete | Check for `AppIcon` in asset catalog with all required sizes | High | Provide all required icon sizes (16, 32, 64, 128, 256, 512, 1024 pt) |

---

## Submission Workflow

When the app passes all audit categories, follow this workflow for submission:

1. **Archive in Xcode.** Product → Archive (requires a Distribution signing identity). Verify zero warnings in Release configuration.
2. **Upload to App Store Connect.** Use the Organizer window (Distribute App → App Store Connect) or `xcodebuild -exportArchive`. Transporter also works.
3. **TestFlight internal testing.** Available to your team within minutes of processing. Walk through every screen on at least two Mac configurations.
4. **TestFlight external testing.** External groups require Beta App Review (usually < 24 hours). Validate with real users before full submission.
5. **Submit for App Review.** In App Store Connect, select the build, fill all metadata, attach screenshots, click Submit. Average review time is under 24 hours; allow 48 hours.

### Phased Release

After approval, you can enable phased release for gradual rollout:

| Day | Percentage of Users |
|-----|---------------------|
| 1   | 1%                  |
| 2   | 2%                  |
| 3   | 5%                  |
| 4   | 10%                 |
| 5   | 20%                 |
| 6   | 50%                 |
| 7   | 100%                |

Users who manually check for updates receive the update immediately regardless of phased release stage. You can pause, resume, or complete the rollout at any time from App Store Connect.

### Expedited Review Requests

Apple grants expedited reviews for critical situations only:
- Critical bug fix affecting existing users
- Time-sensitive event (holiday launch, legal compliance deadline)
- Security vulnerability patch

Request via the Contact Us form in App Store Connect (App Review → Expedite Request). Provide a specific, factual justification.

---

## Appeal Process

If your app is rejected, all rejections appear in the **Resolution Center** in App Store Connect:

1. **Read the rejection carefully** — it cites the specific guideline violated.
2. **Reply in the Resolution Center** with a clear, factual explanation.
3. **If you fixed the issue**, describe exactly what changed and resubmit the binary.
4. **If you believe the rejection is incorrect**, explain why your app complies with references to the specific guideline text.

**Tone matters.** Be professional, specific, and concise. Provide demo credentials, screenshots, or screen recordings that demonstrate compliance.

### Escalation to App Review Board

If the Resolution Center exchange does not resolve the issue:
1. Request an appeal to the **App Review Board** via the Resolution Center or the App Store Contact form (App Review → Appeal).
2. The Board is a separate team from the original reviewer. Provide all context.
3. Board decisions are final for that submission, but you can modify and resubmit.

### Successful Appeal Strategies

- **Provide a video walkthrough** showing the feature the reviewer could not find.
- **Cite the specific guideline** and explain how the app satisfies each requirement.
- **Include demo credentials** if the reviewer could not log in.
- **Reference precedent** — if similar macOS apps exist on the App Store with the same pattern, note them respectfully.
- **Offer a compromise** — if Apple objects to a specific implementation, propose an alternative.

---

## Common Mistakes Quick Reference

These are the most frequent reasons macOS apps get rejected. Use this as a final sanity check before submission:

1. **Missing demo credentials** — Provide App Review login credentials in App Store Connect notes. Most Guideline 2.1 rejections are from reviewers unable to test behind a login.
2. **Privacy manifest mismatch** — Declared data collection in `PrivacyInfo.xcprivacy` must match App Store privacy nutrition labels and actual network traffic. Apple cross-references all three.
3. **Unnecessary ATT prompt** — Do not show the App Tracking Transparency prompt unless you actually track users across apps/websites. Apple rejects unnecessary prompts.
4. **Vague usage descriptions** — "This app needs your location" is rejected. State the specific feature that uses the data.
5. **External payment links for digital content** — Any language or button directing users to purchase digital content outside the app is rejected.
6. **Missing App Sandbox** — Mac App Store apps without sandbox enabled will be automatically rejected.
7. **Hardened Runtime not enabled** — Required for notarization and Mac App Store submission.
8. **Temporary exception entitlements** — These are heavily scrutinized and often rejected. Find alternatives.
9. **Placeholder content visible** — Remove all TODO, lorem ipsum, test data, and placeholder images before submission.
10. **Screenshots don't match actual UI** — Screenshots must show the real app, not mockups or marketing renders.

---

## HTML Report Template

Generate a self-contained HTML file using this structure. The CSS should be inline — no external dependencies.

```
Structure:
├── Header
│   ├── Title: "macOS App Store Readiness Report"
│   ├── App name, Bundle ID, scan date
│   └── Readiness gauge (percentage with color coding)
├── Executive Summary
│   ├── PASS / WARN / FAIL counts
│   └── Overall readiness score with gauge
├── Category Summary Table
│   └── One row per category: name, status badge, finding count, summary
├── Detailed Findings (collapsible per category)
│   └── Each finding: severity badge, check name, description, remediation
├── Remediation Priority (action plan)
│   └── Ordered list of all Critical/High findings with specific fix instructions
└── Footer
    ├── Generation timestamp
    └── Disclaimer about manual review requirements
```

**CSS Styling Guidelines:**
- Dark header (`#1a1a2e` background, white text)
- Severity badges: Critical = `#dc3545`, High = `#fd7e14`, Medium = `#ffc107`, Low = `#6c757d`
- Status badges: PASS = `#28a745`, WARN = `#ffc107`, FAIL = `#dc3545`
- Readiness gauge: Red (< 60%), Yellow (60-85%), Green (> 85%)
- Use `<details>` / `<summary>` for collapsible category sections
- Alternating row colors for tables
- Responsive layout for readability on different screen sizes

---

## References

- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [App Sandbox](https://developer.apple.com/documentation/security/app_sandbox)
- [Hardened Runtime](https://developer.apple.com/documentation/security/hardened_runtime)
- [Notarizing macOS Software](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Privacy Manifest Files](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files)
- [Required Reason API Codes](https://developer.apple.com/documentation/bundleresources/privacy_manifest_files/required_reason_api_codes)
- [Entitlements](https://developer.apple.com/documentation/bundleresources/entitlements)
- [macOS Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos)
- [Information Property List](https://developer.apple.com/documentation/bundleresources/information_property_list)
- [Code Signing](https://developer.apple.com/support/code-signing)
- [App Store Connect Help](https://developer.apple.com/help/app-store-connect/)
- [App Tracking Transparency](https://developer.apple.com/documentation/apptrackingtransparency)
- [StoreKit 2](https://developer.apple.com/documentation/storekit)
